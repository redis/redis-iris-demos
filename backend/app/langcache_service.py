from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.query.filter import FilterExpression, Tag
from redisvl.utils.vectorize import OpenAITextVectorizer

from backend.app.settings import Settings

log = logging.getLogger("iris.langcache")


FILTERABLE_ATTRIBUTE_FIELDS = ("domain", "access_class", "cache_group_id", "topic")


class LangCacheService:
    """RedisVL-backed semantic cache used by the demo LangCache surface."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache_id = settings.langcache_cache_id or f"{settings.demo_domain}_langcache"
        self._threshold = self._distance_threshold(settings.langcache_threshold)
        self._cache: SemanticCache | None = None

    @staticmethod
    def _distance_threshold(raw_threshold: float) -> float:
        # Existing .env values are semantic-similarity thresholds. RedisVL
        # SemanticCache expects cosine distance, where lower is stricter.
        if 0 <= raw_threshold <= 1:
            return 1 - raw_threshold
        return raw_threshold

    def is_configured(self) -> bool:
        return bool(
            self._cache_id
            and self._settings.openai_api_key
            and self._settings.redis_host
            and self._settings.redis_port
        )

    def _redis_url(self) -> str:
        scheme = "rediss" if self._settings.redis_ssl else "redis"
        username = quote(self._settings.redis_username or "default", safe="")
        password = quote(self._settings.redis_password, safe="")
        auth = f"{username}:{password}@" if password else f"{username}@"
        return f"{scheme}://{auth}{self._settings.redis_host}:{self._settings.redis_port}/{self._settings.redis_db}"

    def _get_cache(self) -> SemanticCache:
        if self._cache is None:
            vectorizer = OpenAITextVectorizer(
                model=self._settings.openai_embedding_model,
                api_config={"api_key": self._settings.openai_api_key},
            )
            self._cache = SemanticCache(
                name=self._cache_id,
                distance_threshold=self._threshold,
                vectorizer=vectorizer,
                filterable_fields=[
                    {"name": field_name, "type": "tag"}
                    for field_name in FILTERABLE_ATTRIBUTE_FIELDS
                ],
                redis_url=self._redis_url(),
            )
        return self._cache

    def _filter_expression(self, attributes: dict[str, str] | None) -> FilterExpression | None:
        if not attributes:
            return None
        expression: FilterExpression | None = None
        for key, value in attributes.items():
            if key not in FILTERABLE_ATTRIBUTE_FIELDS or value is None:
                continue
            current = Tag(key) == str(value)
            expression = current if expression is None else expression & current
        return expression

    async def search(self, prompt: str, attributes: dict[str, str] | None = None) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        def _check() -> list[dict[str, Any]]:
            return self._get_cache().check(
                prompt=prompt,
                num_results=1,
                filter_expression=self._filter_expression(attributes),
            )

        try:
            entries = await asyncio.to_thread(_check)
            if entries:
                best = entries[0]
                distance = float(best.get("vector_distance", 1.0))
                similarity = max(0.0, min(1.0, 1.0 - distance))
                log.info("Cache HIT (similarity=%.3f): %s", similarity, prompt[:60])
                return {
                    "hit": True,
                    "similarity": similarity,
                    "response": best.get("response", ""),
                    "prompt": best.get("prompt", ""),
                }
            log.info("Cache MISS: %s", prompt[:60])
            return None
        except Exception as exc:
            log.warning("LangCache search failed: %s", exc)
            return None

    async def store(self, prompt: str, response: str, attributes: dict[str, str] | None = None) -> bool:
        if not self.is_configured():
            return False

        def _store() -> str:
            return self._get_cache().store(
                prompt=prompt,
                response=response,
                filters=attributes or None,
            )

        try:
            await asyncio.to_thread(_store)
            log.info("Stored cache entry: %s", prompt[:60])
            return True
        except Exception as exc:
            log.warning("LangCache store failed: %s", exc)
            return False

    async def flush(self) -> bool:
        if not self.is_configured():
            return False

        try:
            await asyncio.to_thread(self._get_cache().clear)
            log.info("Flushed all LangCache entries")
            return True
        except Exception as exc:
            log.warning("LangCache flush failed: %s", exc)
            return False

    async def close(self) -> None:
        if self._cache:
            await asyncio.to_thread(self._cache.disconnect)
            self._cache = None
