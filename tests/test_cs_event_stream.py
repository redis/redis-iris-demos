"""Context Surface SSE stream contract tests.

These guard the fix for stalled tool-call traces: every tool-call must be
followed by a terminal ``tool-result`` even when the tool errors, when
LangGraph omits the ``run_id``, or when the agent loop raises mid-stream.
"""

from __future__ import annotations

import os

# main.py constructs OpenAI-backed services at import time.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import asyncio
import json

import backend.app.main as main_mod
from backend.app.contracts import ChatRequest


def _decode_sse_payload(chunk: str) -> dict:
    payload = chunk.removeprefix("data: ").split("\n\n", 1)[0].strip()
    return json.loads(payload)


async def _collect_chat_events(request: ChatRequest) -> list[dict]:
    out = []
    async for chunk in main_mod.cs_event_stream(request):
        out.append(_decode_sse_payload(chunk))
    return out


def _chat_request() -> ChatRequest:
    return ChatRequest(messages=[{"role": "user", "content": "hello"}], thread_id="test-thread")


def _disable_preamble(monkeypatch) -> None:
    """Skip the guardrail/cache/memory phases so tests exercise the agent loop only."""
    monkeypatch.setattr(main_mod.guardrail_service, "is_configured", lambda: False)
    monkeypatch.setattr(main_mod.langcache_service, "is_configured", lambda: False)
    monkeypatch.setattr(main_mod.memory_service, "is_configured", lambda: False)
    monkeypatch.setitem(main_mod.runtime_config, "enable_post_model_verifier", False)


def _use_fake_agent(monkeypatch, agent) -> None:
    async def fake_get_agent(*_args, **_kwargs):
        return agent

    monkeypatch.setattr(main_mod, "get_agent", fake_get_agent)


def test_cs_event_stream_emits_terminal_tool_result_on_tool_error(monkeypatch):
    class FakeAgent:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_tool_start",
                "name": "filter_order_by_customer_id",
                "run_id": "tool-1",
                "data": {"input": {"value": "CUST_DEMO_001"}},
            }
            yield {
                "event": "on_tool_error",
                "name": "filter_order_by_customer_id",
                "run_id": "tool-1",
                "data": {"error": ValueError("missing required field: value")},
            }

    _disable_preamble(monkeypatch)
    _use_fake_agent(monkeypatch, FakeAgent())

    events = asyncio.run(_collect_chat_events(_chat_request()))
    tool_results = [event for event in events if event["type"] == "tool-result"]

    assert len(tool_results) == 1
    assert tool_results[0]["toolName"] == "filter_order_by_customer_id"
    assert tool_results[0]["payload"]["error"] == "missing required field: value"
    assert tool_results[0]["payload"]["type"] == "ValueError"
    assert tool_results[0]["durationMs"] >= 1
    assert events[-1]["type"] == "done"


def test_cs_event_stream_matches_missing_run_id_tool_error_to_pending_call(monkeypatch):
    class FakeAgent:
        async def astream_events(self, *_args, **_kwargs):
            # No run_id on either event — must still resolve by tool name.
            yield {
                "event": "on_tool_start",
                "name": "filter_order_by_customer_id",
                "data": {"input": {"value": "CUST_DEMO_001"}},
            }
            yield {
                "event": "on_tool_error",
                "name": "filter_order_by_customer_id",
                "data": {"error": ValueError("missing required field: value")},
            }

    _disable_preamble(monkeypatch)
    _use_fake_agent(monkeypatch, FakeAgent())

    events = asyncio.run(_collect_chat_events(_chat_request()))
    tool_call = next(event for event in events if event["type"] == "tool-call")
    tool_results = [event for event in events if event["type"] == "tool-result"]

    assert tool_call["toolName"] == "filter_order_by_customer_id"
    assert len(tool_results) == 1
    assert tool_results[0]["toolName"] == "filter_order_by_customer_id"
    assert tool_results[0]["payload"]["error"] == "missing required field: value"
    assert events[-1]["type"] == "done"


def test_cs_event_stream_flushes_pending_tool_result_before_stream_error(monkeypatch):
    class FakeAgent:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_tool_start",
                "name": "filter_order_by_customer_id",
                "run_id": "tool-1",
                "data": {"input": {"value": "CUST_DEMO_001"}},
            }
            raise RuntimeError("stream failed after tool call")

    _disable_preamble(monkeypatch)
    _use_fake_agent(monkeypatch, FakeAgent())

    events = asyncio.run(_collect_chat_events(_chat_request()))
    event_types = [event["type"] for event in events]
    tool_result_index = event_types.index("tool-result")
    error_index = event_types.index("error")

    assert tool_result_index < error_index
    assert events[tool_result_index]["toolName"] == "filter_order_by_customer_id"
    assert events[tool_result_index]["payload"]["error"] == "stream failed after tool call"
    assert "errorType" in events[error_index]
    assert events[-1]["type"] == "done"
