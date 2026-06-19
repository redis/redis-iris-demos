"""Internal tools that run locally, defined by the active domain."""

from __future__ import annotations

import asyncio
from inspect import signature
from typing import Any

from backend.app.core.domain_contract import InternalToolDefinition
from backend.app.core.domain_loader import get_active_domain
from backend.app.settings import DEFAULT_MEMORY_SIMILARITY_THRESHOLD, Settings


def effective_memory_similarity_threshold(
    settings: Settings,
    runtime_config: dict[str, Any],
) -> float:
    if settings.memory_similarity_threshold is not None:
        return float(settings.memory_similarity_threshold)
    runtime_threshold = runtime_config.get("memory_similarity_threshold")
    if runtime_threshold is not None:
        return float(runtime_threshold)
    return DEFAULT_MEMORY_SIMILARITY_THRESHOLD


def _accepts_runtime_config(callable_obj: Any) -> bool:
    try:
        return "runtime_config" in signature(callable_obj).parameters
    except (TypeError, ValueError):
        return False


def domain_runtime_config(domain: Any, settings: Settings) -> dict[str, Any]:
    getter = getattr(domain, "get_runtime_config", None)
    runtime_config: dict[str, Any] = {}
    if callable(getter):
        runtime_config = dict(getter(settings=settings) or {})
    runtime_config["memory_similarity_threshold"] = effective_memory_similarity_threshold(
        settings,
        runtime_config,
    )
    return runtime_config


def internal_tool_names(settings: Settings) -> list[str]:
    domain = get_active_domain(settings)
    runtime_config = domain_runtime_config(domain, settings)
    return [tool.name for tool in domain.get_internal_tool_definitions(runtime_config=runtime_config)]


class InternalToolService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.domain = get_active_domain(settings)

    @property
    def definitions(self) -> tuple[InternalToolDefinition, ...]:
        runtime_config = domain_runtime_config(self.domain, self.settings)
        return tuple(self.domain.get_internal_tool_definitions(runtime_config=runtime_config))

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.domain.execute_internal_tool(tool_name, arguments, self.settings)

    async def aexecute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async_executor = getattr(self.domain, "aexecute_internal_tool", None)
        if callable(async_executor):
            if _accepts_runtime_config(async_executor):
                runtime_config = domain_runtime_config(self.domain, self.settings)
                return await async_executor(
                    tool_name,
                    arguments,
                    self.settings,
                    runtime_config=runtime_config,
                )
            return await async_executor(tool_name, arguments, self.settings)
        return await asyncio.to_thread(self.execute, tool_name, arguments)
