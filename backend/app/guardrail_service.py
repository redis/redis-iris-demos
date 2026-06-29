"""Semantic routing guardrail using redisvl SemanticRouter.

Routes are loaded from the active domain's GuardrailConfig. If the domain
has no guardrail config, the service reports is_configured() == False and
all checks are skipped.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI
from redisvl.extensions.router import Route, SemanticRouter
from redisvl.extensions.router.schema import RoutingConfig
from redisvl.utils.vectorize import OpenAITextVectorizer

from backend.app.core.domain_contract import GuardrailConfig
from backend.app.redis_connection import build_redis_url
from backend.app.settings import Settings

log = logging.getLogger("iris.guardrail")


class GuardrailService:
    def __init__(self, settings: Settings, guardrail_config: GuardrailConfig | None = None) -> None:
        self._openai_api_key = settings.openai_api_key
        self._embedding_model = settings.openai_embedding_model
        self._redis_url = build_redis_url(settings)
        self._enabled = settings.guardrail_enabled
        self._config = guardrail_config
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self._router: SemanticRouter | None = None
        self._lock = asyncio.Lock()
        self._block_messages: dict[str, str] = {
            route.name: route.block_message
            for route in (guardrail_config.routes if guardrail_config else [])
            if route.block_message
        }

    def is_configured(self) -> bool:
        return bool(self._enabled and self._config and self._openai_api_key and self._redis_url)

    async def _ensure_router(self) -> SemanticRouter:
        if self._router is not None:
            return self._router
        async with self._lock:
            if self._router is not None:
                return self._router
            if not self._config:
                raise RuntimeError("No guardrail config provided")

            vectorizer = OpenAITextVectorizer(
                model=self._embedding_model,
                api_config={"api_key": self._openai_api_key},
            )

            routes = [
                Route(
                    name=route_cfg.name,
                    references=route_cfg.references,
                    distance_threshold=route_cfg.distance_threshold,
                )
                for route_cfg in self._config.routes
            ]

            router_name = self._config.router_name

            def _build() -> SemanticRouter:
                return SemanticRouter(
                    name=router_name,
                    vectorizer=vectorizer,
                    routes=routes,
                    # Classify on the single closest reference ("min") rather than the
                    # default per-route average. Attack/intent routes (e.g. unauthorized
                    # access) carry many phrasing variants; one strong match should fire
                    # the route instead of being diluted by less-similar references.
                    routing_config=RoutingConfig(aggregation_method="min"),
                    redis_url=self._redis_url,
                    overwrite=True,
                )

            self._router = await asyncio.to_thread(_build)
            log.info("Semantic router '%s' initialized (%d routes)", router_name, len(routes))
            return self._router

    async def embed(self, text: str) -> list[float]:
        resp = await self._openai.embeddings.create(
            input=[text],
            model=self._embedding_model,
        )
        return resp.data[0].embedding

    async def check(self, vector: list[float]) -> dict[str, Any]:
        if not self._config:
            return {"allowed": True, "route": None, "distance": None, "block_message": None}
        try:
            router = await self._ensure_router()
            match = await asyncio.to_thread(router, None, vector)
            allowed = match.name == self._config.allowed_route_name
            block_message = None if allowed else self._block_messages.get(match.name)
            return {
                "allowed": allowed,
                "route": match.name,
                "distance": match.distance,
                "block_message": block_message,
            }
        except Exception:
            log.warning("Guardrail check failed, allowing through", exc_info=True)
            return {"allowed": True, "route": None, "distance": None, "block_message": None}

    async def warm_up(self) -> None:
        if self.is_configured():
            await self._ensure_router()
            log.info("Guardrail service warmed up")

    async def close(self) -> None:
        pass
