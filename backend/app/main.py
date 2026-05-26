from __future__ import annotations

import atexit
import asyncio
import base64
import json
import logging
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage

from backend.app.domain_events import stream_domain_events
from backend.app.context_surface_service import ContextSurfaceService
from backend.app.core.domain_contract import InternalToolAccessControl
from backend.app.core.domain_loader import get_active_domain
from backend.app.contracts import ChatRequest
from backend.app.internal_tools import InternalToolService, domain_runtime_config, internal_tool_names
from backend.app.langgraph_agent import create_agent, create_checkpointer
from backend.app.request_context import request_context_scope
from backend.app.rag_service import SimpleRAGService
from backend.app.semantic_cache import SemanticCacheService
from backend.app.sse import format_sse_event
from backend.app.settings import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
domain = get_active_domain(settings)
ROOT_DIR = Path(__file__).resolve().parents[2]
app = FastAPI(title=f"{domain.manifest.branding.app_name} Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin, "http://localhost:3040", "http://127.0.0.1:3040"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

internal_tools = InternalToolService(settings)
cs_service = ContextSurfaceService(settings)
rag_service = SimpleRAGService(settings, cs_service)
runtime_config = domain_runtime_config(domain, settings)
semantic_cache_service = SemanticCacheService(settings, domain)

_langgraph_agent = None
_checkpointer = None
_cleanup_lock = Lock()
_background_resources_cleaned = False


async def get_agent():
    global _langgraph_agent, _checkpointer
    if _langgraph_agent is None:
        _checkpointer = await create_checkpointer(settings)
        _langgraph_agent = await create_agent(settings, internal_tools, cs_service, _checkpointer)
    return _langgraph_agent


class Timer:
    def __init__(self) -> None:
        self._start = perf_counter()
        self._lap = self._start

    def elapsed_ms(self) -> int:
        return round((perf_counter() - self._start) * 1000)

    def lap_ms(self) -> int:
        now = perf_counter()
        delta = round((now - self._lap) * 1000)
        self._lap = now
        return max(delta, 1)


def _logo_src(path: Path) -> str:
    suffix = path.suffix.lower()
    mime_type = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


_INTERNAL_NAMES: set[str] | None = None
_INTERNAL_TOOL_ACCESS: dict[str, InternalToolAccessControl] | None = None


def _tool_kind(name: str) -> str:
    global _INTERNAL_NAMES
    if _INTERNAL_NAMES is None:
        _INTERNAL_NAMES = {t.name for t in internal_tools.definitions}
    return "internal_function" if name in _INTERNAL_NAMES else "mcp_tool"


def _internal_tool_access_control(name: str) -> InternalToolAccessControl:
    global _INTERNAL_TOOL_ACCESS
    if _INTERNAL_TOOL_ACCESS is None:
        _INTERNAL_TOOL_ACCESS = {
            tool.name: tool.access_control
            for tool in internal_tools.definitions
        }
    return _INTERNAL_TOOL_ACCESS.get(name, InternalToolAccessControl())


def _short_input(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("query", "text", "product_id", "store_id", "order_id", "shipment_id", "tracking_number", "customer_id"):
            value = payload.get(key)
            if value:
                return str(value)
    if payload is None:
        return ""
    return str(payload)


def _thinking_step_for_tool(name: str, payload: Any) -> str | None:
    if hasattr(domain, "describe_tool_trace_step"):
        custom = domain.describe_tool_trace_step(tool_name=name, payload=payload, runtime_config=runtime_config)
        if custom is not None:
            return custom or None

    detail = _short_input(payload)
    if name == domain.manifest.identity.tool_name:
        return "Identify the signed-in user context before using live account data."
    if name == "get_current_time":
        return "Compare live timestamps against relevant dates and status windows."
    if name.startswith("search_"):
        return f"Search domain data using: {detail or 'the current query'}."
    if name.startswith("filter_"):
        return "Filter live domain records to narrow the relevant results."
    if name.startswith("get_"):
        return "Fetch the exact record needed for the current question."
    return None


def _format_elapsed_ms(duration_ms: int) -> str:
    if duration_ms >= 1000:
        return f"{duration_ms / 1000:.1f}s"
    return f"{duration_ms}ms"


def _llm_phase_label(*, llm_call_index: int, tool_calls_seen: int) -> str:
    if llm_call_index == 1 and tool_calls_seen == 0:
        return "Plan the next action and decide whether tools are needed."
    if tool_calls_seen > 0:
        return "Review tool results and decide the next step."
    return "Reason about the request and decide the next step."


def _domain_demo_users() -> list[dict[str, Any]]:
    getter = getattr(domain, "get_demo_users", None)
    if not callable(getter):
        return []
    return [user.model_dump() if hasattr(user, "model_dump") else dict(user) for user in getter()]


def _resolve_demo_user(request: ChatRequest) -> dict[str, Any] | None:
    resolver = getattr(domain, "resolve_demo_user", None)
    if not callable(resolver):
        return None
    selected_id = request.demo_user_id or domain.manifest.identity.default_id
    resolved = resolver(selected_id)
    if resolved is None and request.demo_user_id:
        raise HTTPException(status_code=400, detail=f"Unknown demo user: {request.demo_user_id}")
    return resolved


def _effective_thread_id(request: ChatRequest, demo_user: dict[str, Any] | None) -> str:
    raw_thread_id = request.thread_id or str(uuid4())
    if demo_user:
        identity = domain.manifest.identity
        user_key = str(demo_user.get(identity.id_field) or request.demo_user_id or identity.default_id)
    else:
        user_key = "anonymous"
    return f"{domain.manifest.id}:{user_key}:{raw_thread_id}"


def _semantic_cache_lookup_block_reason(question: str) -> str | None:
    normalized = question.lower().replace("’", "'")
    user_specific_phrases = (
        "my flight",
        "my trip",
        "my booking",
        "my reservation",
        "my itinerary",
        "my support case",
        "my case",
        "my ticket",
        "my profile",
        "my email",
        "on file",
        "email do you have",
        "customer id",
        "record locator",
        "booking reference",
        "pnr",
    )
    if any(phrase in normalized for phrase in user_specific_phrases):
        return "prompt requires live user-specific context"

    account_terms = (
        "account",
        "booking",
        "case",
        "customer id",
        "disrupted",
        "email",
        "itinerary",
        "profile",
        "reaccommodation",
        "rebooked",
        "record locator",
        "reservation",
        "support case",
        "ticket",
    )
    personal_terms = (" my ", " me ", " i ", " i'm ")
    padded = f" {normalized} "
    if any(term in normalized for term in account_terms) and any(term in padded for term in personal_terms):
        return "prompt requires live user-specific context"

    return None


def _cleanup_process_resources() -> None:
    global _background_resources_cleaned
    with _cleanup_lock:
        if _background_resources_cleaned:
            return
        _background_resources_cleaned = True

    semantic_cache_service.close()


atexit.register(_cleanup_process_resources)


@app.on_event("startup")
async def startup_resources() -> None:
    if semantic_cache_service.enabled:
        await asyncio.to_thread(semantic_cache_service.warmup)


@app.on_event("shutdown")
async def shutdown_resources() -> None:
    await semantic_cache_service.aclose()
    _cleanup_process_resources()
    global _checkpointer
    if _checkpointer is not None and hasattr(_checkpointer, "__aexit__"):
        try:
            await _checkpointer.__aexit__(None, None, None)
        except Exception:
            log.exception("Unable to close LangGraph checkpointer cleanly")


@app.get("/api/health")
async def health() -> JSONResponse:
    mcp_tool_names = [tool.get("name", "") for tool in await cs_service.list_tools()]
    return JSONResponse({
        "ok": True,
        "domain": domain.manifest.id,
        "mcp_enabled": bool(settings.mcp_agent_key),
        "internal_tools": internal_tool_names(settings),
        "mcp_tools": [name for name in mcp_tool_names if name],
    })


@app.get("/api/domain-config")
async def domain_config() -> JSONResponse:
    branding = domain.manifest.branding
    demo_users = _domain_demo_users()
    return JSONResponse({
        "id": domain.manifest.id,
        "app_name": branding.app_name,
        "subtitle": branding.subtitle,
        "hero_title": branding.hero_title,
        "placeholder_text": branding.placeholder_text,
        "starter_prompts": [card.model_dump() for card in branding.starter_prompts],
        "theme": branding.theme.model_dump(),
        "ui": branding.ui.model_dump(),
        "logo_src": _logo_src(ROOT_DIR / branding.logo_path),
        "semantic_cache_enabled": bool(semantic_cache_service.enabled),
        "demo_users": demo_users,
        "default_demo_user_id": demo_users[0]["id"] if demo_users else None,
    })


async def cs_event_stream(request: ChatRequest) -> AsyncIterator[str]:
    timer = Timer()
    yield format_sse_event("status", text="Initializing agent…", ts=timer.elapsed_ms())

    agent = await get_agent()
    defer_final_answer = runtime_config.get("enable_post_model_verifier", False)

    latest_message = request.messages[-1].content if request.messages else ""
    demo_user = _resolve_demo_user(request)
    thread_id = _effective_thread_id(request, demo_user)
    cache_group_id = ""

    config = {"configurable": {"thread_id": thread_id}}
    if demo_user:
        cache_group_id = str(demo_user.get("cache_group_id") or "")

    with request_context_scope(demo_user_id=request.demo_user_id, demo_user=demo_user):
        cache_write_flags = {"public": False, "group": False, "non_cacheable": False}
        cache_provenance = {"public": set(), "group": set(), "non_cacheable": set()}
        cache_lookup_eligible = False
        cache_reason = ""
        streamed_text: list[str] = []

        if semantic_cache_service.enabled:
            cache_lookup_block_reason = _semantic_cache_lookup_block_reason(latest_message)
            cache_lookup_eligible = (
                len(request.messages) == 1
                and cache_lookup_block_reason is None
                and await semantic_cache_service.thread_is_fresh(agent, config)
            )
            cache_request_payload = {
                "question": latest_message,
                "eligible": cache_lookup_eligible,
                "cacheGroupId": cache_group_id or None,
            }
            cache_hit = None
            cache_outcome = "skip"
            cache_duration_ms = 1
            if cache_lookup_block_reason:
                cache_reason = cache_lookup_block_reason
            elif not cache_lookup_eligible:
                cache_reason = "single-turn cache requires a fresh thread"
            else:
                cache_request_payload["filterPolicy"] = semantic_cache_service.build_filter_policy(
                    group_id=cache_group_id or None
                )
                cache_started = perf_counter()
                cache_outcome = "pending"
                try:
                    cache_hit = await semantic_cache_service.check(
                        prompt=latest_message,
                        group_id=cache_group_id or None,
                    )
                except Exception:
                    log.exception("Semantic cache lookup failed")
                    cache_hit = None
                    cache_outcome = "skip"
                    cache_reason = "semantic cache lookup failed"
                cache_duration_ms = max(round((perf_counter() - cache_started) * 1000), 1)
                if cache_outcome != "skip":
                    cache_outcome = "hit" if cache_hit is not None else "miss"

            if cache_hit is not None and cache_outcome == "hit":
                persisted = await semantic_cache_service.persist_cached_turn(
                    agent=agent,
                    config=config,
                    question=latest_message,
                    answer=cache_hit.response,
                )
                if persisted:
                    cache_run_id = f"cache-hit-{uuid4()}"
                    yield format_sse_event(
                        "tool-call",
                        toolName="Semantic cache hit",
                        toolKind="cache",
                        runId=cache_run_id,
                        payload=cache_request_payload,
                        ts=timer.elapsed_ms(),
                    )
                    yield format_sse_event(
                        "tool-result",
                        toolName="Semantic cache hit",
                        toolKind="cache",
                        runId=cache_run_id,
                        payload={
                            "result": "hit",
                            "accessClass": cache_hit.filters.get("access_class") or None,
                            "groupId": cache_hit.filters.get("group_id") or None,
                        },
                        durationMs=cache_duration_ms,
                        ts=timer.elapsed_ms(),
                    )
                    yield format_sse_event("status", text="Semantic cache hit. Reusing a matching standalone answer.", ts=timer.elapsed_ms())
                    yield format_sse_event("text-delta", delta=cache_hit.response)
                    yield format_sse_event("done", totalElapsedMs=timer.elapsed_ms())
                    return
                cache_outcome = "skip"
                cache_reason = "cached turn could not be persisted into thread state"

            if cache_outcome == "skip":
                cache_run_id = f"cache-skip-{uuid4()}"
                yield format_sse_event(
                    "tool-call",
                    toolName="Semantic cache skip",
                    toolKind="cache",
                    runId=cache_run_id,
                    payload=cache_request_payload,
                    ts=timer.elapsed_ms(),
                )
                cache_result_payload: dict[str, Any] = {
                    "result": "skip",
                    "reason": cache_reason,
                }
            elif cache_outcome == "miss":
                cache_run_id = f"cache-miss-{uuid4()}"
                yield format_sse_event(
                    "tool-call",
                    toolName="Semantic cache miss",
                    toolKind="cache",
                    runId=cache_run_id,
                    payload=cache_request_payload,
                    ts=timer.elapsed_ms(),
                )
                cache_result_payload = {
                    "result": "miss",
                }
            yield format_sse_event(
                "tool-result",
                toolName="Semantic cache skip" if cache_outcome == "skip" else "Semantic cache miss",
                toolKind="cache",
                runId=cache_run_id,
                payload=cache_result_payload,
                durationMs=cache_duration_ms,
                ts=timer.elapsed_ms(),
            )

        tool_start_times: dict[str, float] = {}
        llm_start_times: dict[str, float] = {}
        llm_step_ids: dict[str, str] = {}
        llm_call_counter = 0
        tool_calls_seen = 0
        last_thinking_step: str | None = None

        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": latest_message}]},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_tool_start":
                name = event.get("name", "")
                tool_input = event["data"].get("input", {})
                tool_start_times[event["run_id"]] = perf_counter()
                tool_calls_seen += 1

                if _tool_kind(name) == "internal_function":
                    access = _internal_tool_access_control(name)
                    if access.access_control_enabled:
                        if access.access_class_override == "public":
                            cache_write_flags["public"] = True
                            cache_provenance["public"].add(name)
                        elif access.access_class_override == "group":
                            cache_write_flags["group"] = True
                            cache_provenance["group"].add(name)
                        elif access.access_class_override == "non-cacheable":
                            cache_write_flags["non_cacheable"] = True
                            cache_provenance["non_cacheable"].add(name)
                else:
                    access_class = semantic_cache_service.classify_mcp_tool(name)
                    if access_class == "public":
                        cache_write_flags["public"] = True
                        cache_provenance["public"].add(name)
                    elif access_class == "group":
                        cache_write_flags["group"] = True
                        cache_provenance["group"].add(name)
                    elif access_class == "non-cacheable":
                        cache_write_flags["non_cacheable"] = True
                        cache_provenance["non_cacheable"].add(name)

                thinking_step = _thinking_step_for_tool(name, tool_input)
                if thinking_step and thinking_step != last_thinking_step:
                    last_thinking_step = thinking_step
                    yield format_sse_event("thinking-step", step=thinking_step, ts=timer.elapsed_ms())
                yield format_sse_event(
                    "tool-call",
                    toolName=name,
                    toolKind=_tool_kind(name),
                    runId=event["run_id"],
                    payload=tool_input if isinstance(tool_input, dict) else {"input": tool_input},
                    ts=timer.elapsed_ms(),
                )

            elif kind == "on_tool_end":
                name = event.get("name", "")
                raw_output = event["data"].get("output", "")
                try:
                    output = json.loads(str(raw_output)) if raw_output else {}
                except (json.JSONDecodeError, TypeError):
                    output = {"result": str(raw_output)}
                if isinstance(output, dict) and output.get("error"):
                    cache_write_flags["non_cacheable"] = True
                    cache_provenance["non_cacheable"].add(f"{name}:error")
                start = tool_start_times.pop(event["run_id"], perf_counter())
                duration_ms = max(round((perf_counter() - start) * 1000), 1)
                yield format_sse_event(
                    "tool-result",
                    toolName=name,
                    toolKind=_tool_kind(name),
                    runId=event["run_id"],
                    payload=output,
                    durationMs=duration_ms,
                    ts=timer.elapsed_ms(),
                )

            elif kind == "on_chat_model_start":
                if not settings.show_llm_trace_steps:
                    continue
                llm_call_counter += 1
                llm_start_times[event["run_id"]] = perf_counter()
                step_id = f"llm-step-{llm_call_counter}"
                llm_step_ids[event["run_id"]] = step_id
                step = _llm_phase_label(llm_call_index=llm_call_counter, tool_calls_seen=tool_calls_seen)
                last_thinking_step = step
                yield format_sse_event(
                    "thinking-step",
                    step=step,
                    stepId=step_id,
                    stepKind="llm",
                    ts=timer.elapsed_ms(),
                )

            elif kind == "on_chat_model_end":
                if not settings.show_llm_trace_steps:
                    continue
                start = llm_start_times.pop(event["run_id"], perf_counter())
                step_id = llm_step_ids.pop(event["run_id"], "")
                duration_ms = max(round((perf_counter() - start) * 1000), 1)
                if step_id:
                    yield format_sse_event(
                        "thinking-step-finish",
                        stepId=step_id,
                        durationMs=duration_ms,
                        durationText=_format_elapsed_ms(duration_ms),
                        ts=timer.elapsed_ms(),
                    )
                else:
                    yield format_sse_event(
                        "status",
                        text=f"LLM step completed in {_format_elapsed_ms(duration_ms)}",
                        ts=timer.elapsed_ms(),
                    )

            elif kind == "on_chat_model_stream":
                if defer_final_answer:
                    continue
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                        streamed_text.append(str(chunk.content))
                        yield format_sse_event("text-delta", delta=chunk.content)

        if defer_final_answer and settings.show_final_verifier_trace_step:
            yield format_sse_event(
                "thinking-step",
                step="Validate the final answer against recent context and tool results.",
                ts=timer.elapsed_ms(),
            )
            yield format_sse_event("status", text="Verifying final answer…", ts=timer.elapsed_ms())

        final_text = ""
        if defer_final_answer:
            if hasattr(agent, "aget_state"):
                snapshot = await agent.aget_state(config)
                messages = snapshot.values.get("messages", []) if snapshot and snapshot.values else []
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                        final_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                        break
            if final_text:
                yield format_sse_event("text-delta", delta=final_text)
        else:
            final_text = "".join(streamed_text).strip()

        if semantic_cache_service.enabled and final_text:
            resolved_store_class, store_reason = semantic_cache_service.resolve_store_access(
                saw_public=cache_write_flags["public"],
                saw_group=cache_write_flags["group"],
                saw_non_cacheable=cache_write_flags["non_cacheable"],
            )
            provenance_summary = {
                "public": sorted(cache_provenance["public"]),
                "group": sorted(cache_provenance["group"]),
                "nonCacheable": sorted(cache_provenance["non_cacheable"]),
            }
            if not cache_lookup_eligible:
                write_run_id = f"cache-write-skip-{uuid4()}"
                write_skip_reason = (
                    store_reason
                    if store_reason == "non-cacheable provenance"
                    else cache_reason or "cache lookup was not eligible"
                )
                yield format_sse_event(
                    "tool-call",
                    toolName="Semantic cache write skip",
                    toolKind="cache",
                    runId=write_run_id,
                    payload={
                        "question": latest_message,
                        "resolvedAccessClass": resolved_store_class,
                        "cacheGroupId": cache_group_id if resolved_store_class == "group" else None,
                        "provenanceSummary": provenance_summary,
                    },
                    ts=timer.elapsed_ms(),
                )
                yield format_sse_event(
                    "tool-result",
                    toolName="Semantic cache write skip",
                    toolKind="cache",
                    runId=write_run_id,
                    payload={"result": "skip", "reason": write_skip_reason},
                    durationMs=1,
                    ts=timer.elapsed_ms(),
                )
            elif resolved_store_class in {"public", "group"} and not (
                resolved_store_class == "group" and not cache_group_id
            ):
                write_started = perf_counter()
                write_skip_reason = ""
                try:
                    stored = await semantic_cache_service.store(
                        prompt=latest_message,
                        response=final_text,
                        access_class=resolved_store_class,
                        group_id=cache_group_id if resolved_store_class == "group" else None,
                        metadata={
                            "resolved_access_class": resolved_store_class,
                            "cache_group_id": cache_group_id if resolved_store_class == "group" else None,
                            "provenance_summary": provenance_summary,
                        },
                    )
                except Exception:
                    log.exception("Semantic cache write failed")
                    stored = None
                    write_skip_reason = "semantic cache write failed"
                if stored:
                    write_request_payload = {
                        "question": latest_message,
                        "resolvedAccessClass": resolved_store_class,
                        "cacheGroupId": cache_group_id if resolved_store_class == "group" else None,
                        "provenanceSummary": provenance_summary,
                    }
                    write_run_id = f"cache-write-{uuid4()}"
                    yield format_sse_event(
                        "tool-call",
                        toolName="Semantic cache write",
                        toolKind="cache",
                        runId=write_run_id,
                        payload=write_request_payload,
                        ts=timer.elapsed_ms(),
                    )
                    yield format_sse_event(
                        "tool-result",
                        toolName="Semantic cache write",
                        toolKind="cache",
                        runId=write_run_id,
                        payload={"result": "stored"},
                        durationMs=max(round((perf_counter() - write_started) * 1000), 1),
                        ts=timer.elapsed_ms(),
                    )
                else:
                    write_run_id = f"cache-write-skip-{uuid4()}"
                    yield format_sse_event(
                        "tool-call",
                        toolName="Semantic cache write skip",
                        toolKind="cache",
                        runId=write_run_id,
                        payload={
                            "question": latest_message,
                            "resolvedAccessClass": resolved_store_class,
                            "cacheGroupId": cache_group_id if resolved_store_class == "group" else None,
                            "provenanceSummary": provenance_summary,
                        },
                        ts=timer.elapsed_ms(),
                    )
                    yield format_sse_event(
                        "tool-result",
                        toolName="Semantic cache write skip",
                        toolKind="cache",
                        runId=write_run_id,
                        payload={"result": "skip", "reason": write_skip_reason or "cache entry was not stored"},
                        durationMs=max(round((perf_counter() - write_started) * 1000), 1),
                        ts=timer.elapsed_ms(),
                    )
            else:
                if resolved_store_class == "group" and not cache_group_id:
                    write_skip_reason = "group provenance without cache group"
                else:
                    write_skip_reason = store_reason
                write_run_id = f"cache-write-skip-{uuid4()}"
                yield format_sse_event(
                    "tool-call",
                    toolName="Semantic cache write skip",
                    toolKind="cache",
                    runId=write_run_id,
                    payload={
                        "question": latest_message,
                        "resolvedAccessClass": resolved_store_class,
                        "cacheGroupId": cache_group_id if resolved_store_class == "group" else None,
                        "provenanceSummary": provenance_summary,
                    },
                    ts=timer.elapsed_ms(),
                )
                yield format_sse_event(
                    "tool-result",
                    toolName="Semantic cache write skip",
                    toolKind="cache",
                    runId=write_run_id,
                    payload={"result": "skip", "reason": write_skip_reason},
                    durationMs=1,
                    ts=timer.elapsed_ms(),
                )

        yield format_sse_event("done", totalElapsedMs=timer.elapsed_ms())


async def rag_event_stream(question: str) -> AsyncIterator[str]:
    timer = Timer()
    async for chunk in rag_service.stream_answer(question, timer):
        yield chunk
    yield format_sse_event("done", totalElapsedMs=timer.elapsed_ms())


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    question = request.messages[-1].content if request.messages else ""
    if request.demo_user_id:
        _resolve_demo_user(request)

    if request.mode == "simple_rag":
        return StreamingResponse(rag_event_stream(question), media_type="text/event-stream")

    return StreamingResponse(
        cs_event_stream(request),
        media_type="text/event-stream",
    )


@app.get("/api/domain-events/stream")
async def domain_events_stream(request: Request, cursor: str = "$", history: int = 12) -> StreamingResponse:
    del request
    return StreamingResponse(
        stream_domain_events(settings, domain, cursor=cursor, history_limit=history),
        media_type="text/event-stream",
    )
