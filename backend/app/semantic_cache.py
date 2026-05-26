from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.query.filter import Tag
from redisvl.utils.vectorize import HFTextVectorizer

from backend.app.redis_connection import build_redis_url
from backend.app.settings import Settings

log = logging.getLogger(__name__)

StoreClass = Literal["public", "group", "non-cacheable", "ignored"]
NO_GROUP_SENTINEL = "__none__"


@dataclass(frozen=True)
class SemanticCacheHit:
    response: str
    metadata: dict[str, Any]
    filters: dict[str, Any]


class SemanticCacheService:
    def __init__(self, settings: Settings, domain: Any):
        self.settings = settings
        self.domain = domain
        self.config = getattr(domain.manifest, "semantic_cache", None)
        self._cache: SemanticCache | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.config and getattr(self.config, "enabled", False))

    def classify_mcp_tool(self, tool_name: str) -> StoreClass:
        classifier = getattr(self.domain, "classify_mcp_semantic_cache_access", None)
        if not callable(classifier):
            return "ignored"
        result = classifier(tool_name=tool_name)
        return result if result in {"public", "group", "non-cacheable"} else "ignored"

    def build_filter_policy(self, *, group_id: str | None) -> dict[str, Any]:
        return {
            "allowPublic": True,
            "groupId": group_id or None,
        }

    def normalize_group_id(self, group_id: Any) -> str:
        raw = str(group_id or "")
        return "" if raw == NO_GROUP_SENTINEL else raw

    def build_read_filter_expression(self, *, group_id: str | None) -> Any:
        domain_expr = (Tag("domain_id") == self.domain.manifest.id) & (Tag("mode") == "context_surfaces") & (
            Tag("model_name") == self.settings.openai_chat_model
        )
        if group_id:
            return domain_expr & (
                (Tag("access_class") == "public")
                | ((Tag("access_class") == "group") & (Tag("group_id") == group_id))
            )
        return domain_expr & (Tag("access_class") == "public")

    def resolve_store_access(
        self,
        *,
        saw_public: bool,
        saw_group: bool,
        saw_non_cacheable: bool,
    ) -> tuple[Literal["public", "group"] | None, str]:
        if saw_non_cacheable:
            return None, "non-cacheable provenance"
        if saw_group:
            return "group", "group provenance"
        if saw_public:
            return "public", "public provenance"
        return None, "no cacheable provenance"

    async def check(
        self,
        *,
        prompt: str,
        group_id: str | None,
    ) -> SemanticCacheHit | None:
        if not self.enabled:
            return None
        filter_expression = self.build_read_filter_expression(group_id=group_id)
        hits = await self._get_cache().acheck(
            prompt=prompt,
            num_results=1,
            return_fields=["response", "metadata", "access_class", "group_id", "domain_id", "mode", "model_name"],
            filter_expression=filter_expression,
        )
        if not hits:
            return None
        hit = hits[0]
        response = str(hit.get("response") or "").strip()
        if not response:
            return None
        metadata = hit.get("metadata")
        return SemanticCacheHit(
            response=response,
            metadata=metadata if isinstance(metadata, dict) else {},
            filters={
                "access_class": str(hit.get("access_class") or ""),
                "group_id": self.normalize_group_id(hit.get("group_id")),
                "domain_id": str(hit.get("domain_id") or ""),
                "mode": str(hit.get("mode") or ""),
                "model_name": str(hit.get("model_name") or ""),
            },
        )

    async def store(
        self,
        *,
        prompt: str,
        response: str,
        access_class: Literal["public", "group"],
        group_id: str | None,
        metadata: dict[str, Any],
    ) -> str | None:
        if not self.enabled:
            return None
        filters = {
            "domain_id": self.domain.manifest.id,
            "mode": "context_surfaces",
            "model_name": self.settings.openai_chat_model,
            "access_class": access_class,
            "group_id": group_id or NO_GROUP_SENTINEL,
        }
        return await self._get_cache().astore(
            prompt=prompt,
            response=response,
            metadata=metadata,
            filters=filters,
            ttl=getattr(self.config, "ttl_seconds", None),
        )

    async def thread_is_fresh(self, agent: Any, config: dict[str, Any]) -> bool:
        if not hasattr(agent, "aget_state"):
            return False
        try:
            snapshot = await agent.aget_state(config)
        except Exception:
            log.exception("Unable to read agent state for semantic-cache freshness check")
            return False
        values = snapshot.values if snapshot and snapshot.values else {}
        messages = values.get("messages", [])
        return not messages

    async def persist_cached_turn(
        self,
        *,
        agent: Any,
        config: dict[str, Any],
        question: str,
        answer: str,
    ) -> bool:
        if not hasattr(agent, "aupdate_state"):
            return False
        try:
            await agent.aupdate_state(
                config,
                {"messages": [HumanMessage(content=question), AIMessage(content=answer)]},
            )
        except Exception:
            log.exception("Unable to persist cached turn into LangGraph state")
            return False
        return True

    def warmup(self, *, text: str = "semantic cache startup warmup") -> None:
        if not self.enabled:
            return
        try:
            cache = self._get_cache()
        except Exception:
            log.exception("Unable to initialize semantic cache during warmup")
            return
        vectorizer = getattr(cache, "_vectorizer", None)
        embed = getattr(vectorizer, "embed", None)
        if not callable(embed):
            return
        try:
            embed(text)
            log.info("Semantic cache vectorizer warmed up")
        except Exception:
            log.exception("Unable to warm up semantic cache vectorizer")

    def close(self) -> None:
        if self._cache is None:
            return
        try:
            self._cache.disconnect()
        except Exception:
            log.exception("Unable to disconnect semantic cache cleanly")
        self._cache = None

    async def aclose(self) -> None:
        if self._cache is None:
            return
        try:
            await self._cache.adisconnect()
        except Exception:
            log.exception("Unable to disconnect semantic cache async client cleanly")
            self.close()
            return
        self._cache = None

    def _get_cache(self) -> SemanticCache:
        if self._cache is not None:
            return self._cache
        self._cache = SemanticCache(
            name=self.config.cache_name,
            distance_threshold=self.config.distance_threshold,
            ttl=self.config.ttl_seconds,
            vectorizer=HFTextVectorizer(
                model=self.settings.semantic_cache_embedding_model,
            ),
            filterable_fields=[
                {"name": "domain_id", "type": "tag"},
                {"name": "mode", "type": "tag"},
                {"name": "model_name", "type": "tag"},
                {"name": "access_class", "type": "tag"},
                {"name": "group_id", "type": "tag"},
            ],
            redis_url=build_redis_url(self.settings),
            connection_kwargs={
                "max_connections": self.settings.redis_max_connections,
                "health_check_interval": 30,
            },
            overwrite=False,
        )
        return self._cache
