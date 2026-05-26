import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from backend.app.core.domain_contract import InternalToolAccessControl
from backend.app.core.domain_loader import load_domain
from backend.app.contracts import ChatMessage, ChatRequest
import backend.app.main as app_main
from backend.app.request_context import request_context_scope
from backend.app.semantic_cache import NO_GROUP_SENTINEL, SemanticCacheHit, SemanticCacheService

AIRLINE_SUPPORT_DOMAIN = load_domain("airline-support")


class FakeSnapshot:
    def __init__(self, messages):
        self.values = {"messages": messages}


class FakeAgent:
    def __init__(self, messages=None):
        self._messages = messages or []
        self.updated = None

    async def aget_state(self, config):
        del config
        return FakeSnapshot(self._messages)

    async def aupdate_state(self, config, values, as_node=None, task_id=None):
        del as_node, task_id
        self.updated = (config, values)
        return config


class FakeStreamingAgent(FakeAgent):
    def __init__(self, events, messages=None):
        super().__init__(messages=messages)
        self._events = events
        self.stream_configs = []

    async def astream_events(self, payload, config, version):
        self.stream_configs.append(config)
        del payload, version
        for event in self._events:
            yield event


class FakeSettings:
    openai_chat_model = "gpt-4o"
    semantic_cache_embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    redis_host = "localhost"
    redis_port = 6379
    redis_username = "default"
    redis_password = ""
    redis_db = 0
    redis_ssl = False


class FakeSemanticCacheRuntime:
    def __init__(self, *, hit=None, persist_result=True, store_result="stored", check_error=None, store_error=None):
        self.enabled = True
        self.hit = hit
        self.persist_result = persist_result
        self.store_result = store_result
        self.check_error = check_error
        self.store_error = store_error
        self.persist_calls = []
        self.store_calls = []
        self.check_calls = []
        self.filter_policy_calls = []
        self.closed = False

    def build_filter_policy(self, *, group_id):
        self.filter_policy_calls.append(group_id)
        return {"allowPublic": True, "groupId": group_id or None}

    async def thread_is_fresh(self, agent, config):
        del agent, config
        return True

    async def check(self, *, prompt, group_id):
        self.check_calls.append({"prompt": prompt, "group_id": group_id})
        if self.check_error is not None:
            raise self.check_error
        return self.hit

    async def persist_cached_turn(self, *, agent, config, question, answer):
        self.persist_calls.append((config, question, answer))
        if not self.persist_result:
            return False
        return await agent.aupdate_state(config, {"messages": [question, answer]}) is not None

    def resolve_store_access(self, *, saw_public, saw_group, saw_non_cacheable):
        if saw_non_cacheable:
            return None, "non-cacheable provenance"
        if saw_group:
            return "group", "group provenance"
        if saw_public:
            return "public", "public provenance"
        return None, "no cacheable provenance"

    async def store(self, *, prompt, response, access_class, group_id, metadata):
        if self.store_error is not None:
            raise self.store_error
        self.store_calls.append(
            {
                "prompt": prompt,
                "response": response,
                "access_class": access_class,
                "group_id": group_id,
                "metadata": metadata,
            }
        )
        return self.store_result

    def classify_mcp_tool(self, tool_name):
        if tool_name.startswith("filter_booking_by_"):
            return "non-cacheable"
        return "public"

    async def aclose(self):
        self.closed = True

    def close(self):
        self.closed = True


class FakeCheckpointer:
    def __init__(self):
        self.exited = False

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert exc_type is None
        assert exc_val is None
        assert exc_tb is None
        self.exited = True


def decode_sse(chunks: list[str]) -> list[dict[str, object]]:
    return [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks if chunk.startswith("data: ")]


def test_airline_support_demo_users_include_shared_group() -> None:
    users = AIRLINE_SUPPORT_DOMAIN.get_demo_users()
    senator_en = [user for user in users if user.cache_group_id == "senator_en"]
    assert len(senator_en) == 2


def test_airline_support_identity_uses_request_scoped_demo_user() -> None:
    demo_user = AIRLINE_SUPPORT_DOMAIN.resolve_demo_user("AIRCUST_002")
    with request_context_scope(demo_user_id="AIRCUST_002", demo_user=demo_user):
        result = AIRLINE_SUPPORT_DOMAIN.execute_internal_tool(
            AIRLINE_SUPPORT_DOMAIN.manifest.identity.tool_name,
            {},
            settings=SimpleNamespace(openai_api_key=""),
        )
    assert result["customer_id"] == "AIRCUST_002"
    assert result["status_tier"] == "Senator"
    assert result["cache_group_id"] == "senator_en"


def test_airline_support_unknown_demo_user_returns_none() -> None:
    assert AIRLINE_SUPPORT_DOMAIN.resolve_demo_user("missing-user") is None


def test_chat_request_rejects_unknown_demo_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I get after a cancellation?")],
        demo_user_id="missing-user",
    )
    with pytest.raises(HTTPException, match="Unknown demo user"):
        app_main._resolve_demo_user(request)


@pytest.mark.parametrize(
    ("prompt", "expected_blocked"),
    [
        ("What help do I usually get after a cancellation?", False),
        ("My flight was disrupted. What happened?", True),
        ("I'm disrupted, what happened?", True),
        ("I’m disrupted, what happened?", True),
        ("What are my rebooking options?", True),
        ("Do I have a support case?", True),
        ("Was I rebooked?", True),
        ("What is my record locator?", True),
        ("What customer ID do you have for me?", True),
        ("What email do you have on file for me?", True),
        ("Show my itinerary.", True),
    ],
)
def test_semantic_cache_lookup_blocks_user_specific_prompt_variants(prompt: str, expected_blocked: bool) -> None:
    reason = app_main._semantic_cache_lookup_block_reason(prompt)
    assert (reason is not None) is expected_blocked


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["context_surfaces", "simple_rag"])
async def test_chat_stream_rejects_unknown_demo_user_before_streaming(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I get after a cancellation?")],
        mode=mode,
        demo_user_id="missing-user",
    )
    with pytest.raises(HTTPException, match="Unknown demo user"):
        await app_main.chat_stream(request)


@pytest.mark.asyncio
async def test_chat_stream_accepts_known_demo_user_before_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I get after a cancellation?")],
        mode="simple_rag",
        demo_user_id="AIRCUST_001",
    )
    response = await app_main.chat_stream(request)
    assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_cs_event_stream_namespaces_thread_state_by_demo_user(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = SimpleNamespace(enabled=False)
    agent = FakeStreamingAgent(
        [
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Live answer.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    for demo_user_id in ("AIRCUST_001", "AIRCUST_003"):
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What are my rebooking options?")],
            thread_id="shared-client-thread",
            demo_user_id=demo_user_id,
        )
        chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
        assert any("Live answer." in chunk for chunk in chunks)

    thread_ids = [
        config["configurable"]["thread_id"]
        for config in agent.stream_configs
    ]
    assert thread_ids == [
        "airline-support:AIRCUST_001:shared-client-thread",
        "airline-support:AIRCUST_003:shared-client-thread",
    ]


def test_semantic_cache_service_classifies_airline_tools() -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    assert service.classify_mcp_tool("search_travelpolicydoc_by_text") == "public"
    assert service.classify_mcp_tool("filter_operatingflight_by_flight_number") == "public"
    assert service.classify_mcp_tool("filter_customerprofile_by_customer_id") == "non-cacheable"
    assert service.classify_mcp_tool("filter_booking_by_customer_id") == "non-cacheable"
    assert service.classify_mcp_tool("search_booking_by_booking_locator") == "non-cacheable"
    assert service.classify_mcp_tool("some_unknown_tool") == "ignored"


@pytest.mark.asyncio
async def test_semantic_cache_service_thread_helpers() -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    fresh_agent = FakeAgent(messages=[])
    used_agent = FakeAgent(messages=["prior"])
    config = {"configurable": {"thread_id": "demo"}}

    assert await service.thread_is_fresh(fresh_agent, config) is True
    assert await service.thread_is_fresh(used_agent, config) is False

    persisted = await service.persist_cached_turn(
        agent=fresh_agent,
        config=config,
        question="When does online check-in open?",
        answer="Online check-in typically opens 23 hours before departure.",
    )
    assert persisted is True
    assert fresh_agent.updated is not None


def test_semantic_cache_service_filter_policy_allows_public_plus_group() -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    assert service.build_filter_policy(group_id=None) == {
        "allowPublic": True,
        "groupId": None,
    }
    assert service.build_filter_policy(group_id="senator_en") == {
        "allowPublic": True,
        "groupId": "senator_en",
    }


def test_semantic_cache_service_filter_expression_scopes_reads() -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    public_expr = service.build_read_filter_expression(group_id=None)
    group_expr = service.build_read_filter_expression(group_id="senator_en")

    public_text = str(public_expr)
    group_text = str(group_expr)
    assert "@domain_id:{airline\\-support}" in public_text
    assert "@access_class:{public}" in public_text
    assert "@access_class:{group}" not in public_text
    assert "@group_id:{senator_en}" in group_text
    assert "@access_class:{group}" in group_text
    assert "@access_class:{public}" in group_text


def test_semantic_cache_service_normalizes_public_group_sentinel() -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    assert service.normalize_group_id(NO_GROUP_SENTINEL) == ""
    assert service.normalize_group_id("senator_en") == "senator_en"


def test_semantic_cache_service_warmup_tolerates_cache_init_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(service, "_get_cache", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    service.warmup()
    assert "Unable to initialize semantic cache during warmup" in caplog.text


@pytest.mark.asyncio
async def test_semantic_cache_service_check_propagates_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(service, "_get_cache", lambda: (_ for _ in ()).throw(RuntimeError("cache unavailable")))

    with pytest.raises(RuntimeError, match="cache unavailable"):
        await service.check(prompt="What help do I get?", group_id="senator_en")


@pytest.mark.asyncio
async def test_semantic_cache_service_store_propagates_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(service, "_get_cache", lambda: (_ for _ in ()).throw(RuntimeError("cache unavailable")))

    with pytest.raises(RuntimeError, match="cache unavailable"):
        await service.store(
            prompt="What help do I get?",
            response="Tier guidance.",
            access_class="group",
            group_id="senator_en",
            metadata={},
        )


@pytest.mark.asyncio
async def test_cs_event_stream_short_circuits_on_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = SemanticCacheHit(
        response="Cached cancellation guidance.",
        metadata={},
        filters={"access_class": "public", "group_id": "", "domain_id": "airline-support", "mode": "context_surfaces", "model_name": "gpt-4o"},
    )
    cache_runtime = FakeSemanticCacheRuntime(hit=cached)
    agent = FakeAgent(messages=[])

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    request = ChatRequest(messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")])
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert any(event["type"] == "tool-call" and event["toolName"] == "Semantic cache hit" for event in events)
    hit_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache hit")
    assert hit_result["payload"]["result"] == "hit"
    assert hit_result["payload"]["groupId"] is None
    assert any(event["type"] == "text-delta" and event["delta"] == "Cached cancellation guidance." for event in events)
    assert cache_runtime.persist_calls


@pytest.mark.asyncio
async def test_cs_event_stream_uses_group_scope_for_cache_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = SemanticCacheHit(
        response="Group-scoped cancellation guidance.",
        metadata={},
        filters={"access_class": "group", "group_id": "senator_en", "domain_id": "airline-support", "mode": "context_surfaces", "model_name": "gpt-4o"},
    )
    cache_runtime = FakeSemanticCacheRuntime(hit=cached)
    agent = FakeAgent(messages=[])

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert cache_runtime.filter_policy_calls == ["senator_en"]
    assert cache_runtime.check_calls == [{"prompt": "What help do I usually get after a cancellation?", "group_id": "senator_en"}]
    hit_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache hit")
    assert hit_result["payload"]["groupId"] == "senator_en"


@pytest.mark.asyncio
async def test_cs_event_stream_skips_cache_read_for_user_specific_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = SemanticCacheHit(
        response="Cached answer should not be reused for a passenger-specific disruption.",
        metadata={},
        filters={"access_class": "group", "group_id": "senator_en", "domain_id": "airline-support", "mode": "context_surfaces", "model_name": "gpt-4o"},
    )
    cache_runtime = FakeSemanticCacheRuntime(hit=cached)
    agent = FakeStreamingAgent(
        [
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Live passenger-specific answer.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="My flight was disrupted. What happened?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert cache_runtime.check_calls == []
    skip_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache skip")
    assert skip_result["payload"]["reason"] == "prompt requires live user-specific context"
    assert any(event["type"] == "text-delta" and event["delta"] == "Live passenger-specific answer." for event in events)


@pytest.mark.asyncio
async def test_cs_event_stream_falls_back_when_cached_turn_cannot_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    cached = SemanticCacheHit(
        response="Cached answer that should not be reused directly.",
        metadata={},
        filters={"access_class": "public", "group_id": "", "domain_id": "airline-support", "mode": "context_surfaces", "model_name": "gpt-4o"},
    )
    cache_runtime = FakeSemanticCacheRuntime(hit=cached, persist_result=False)
    agent = FakeStreamingAgent(
        [
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Live fallback answer.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    request = ChatRequest(messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")])
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    skip_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache skip")
    assert skip_result["payload"]["result"] == "skip"
    assert skip_result["payload"]["reason"] == "cached turn could not be persisted into thread state"
    assert any(event["type"] == "text-delta" and event["delta"] == "Live fallback answer." for event in events)


@pytest.mark.asyncio
async def test_cs_event_stream_falls_back_when_cache_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(check_error=RuntimeError("cache unavailable"))
    agent = FakeStreamingAgent(
        [
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Live answer after cache failure.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)

    request = ChatRequest(messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")])
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    skip_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache skip")
    assert skip_result["payload"]["result"] == "skip"
    assert skip_result["payload"]["reason"] == "semantic cache lookup failed"
    assert any(event["type"] == "text-delta" and event["delta"] == "Live answer after cache failure." for event in events)


@pytest.mark.asyncio
async def test_cs_event_stream_writes_group_cache_for_identity_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None)
    tier_context_tool = "get_current_service_tier_context"
    events = [
        {"event": "on_tool_start", "name": tier_context_tool, "run_id": "tool-1", "data": {"input": {}}},
        {"event": "on_tool_end", "name": tier_context_tool, "run_id": "tool-1", "data": {"output": "{}"}},
        {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Tier guidance.", tool_calls=[])}},
    ]
    agent = FakeStreamingAgent(events, messages=[])

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "internal_function" if name == tier_context_tool else "mcp_tool")
    monkeypatch.setattr(
        app_main,
        "_internal_tool_access_control",
        lambda name: InternalToolAccessControl(access_control_enabled=True, access_class_override="group")
        if name == tier_context_tool
        else InternalToolAccessControl(),
    )

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    decoded = decode_sse(chunks)

    assert cache_runtime.store_calls
    store_call = cache_runtime.store_calls[0]
    assert store_call["access_class"] == "group"
    assert store_call["group_id"] == "senator_en"
    write_event = next(event for event in decoded if event["type"] == "tool-call" and event["toolName"] == "Semantic cache write")
    assert write_event["payload"]["resolvedAccessClass"] == "group"
    assert write_event["payload"]["cacheGroupId"] == "senator_en"


@pytest.mark.asyncio
async def test_cs_event_stream_skips_cache_write_for_identity_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None)
    identity_tool = AIRLINE_SUPPORT_DOMAIN.manifest.identity.tool_name
    agent = FakeStreamingAgent(
        [
            {"event": "on_tool_start", "name": identity_tool, "run_id": "tool-1", "data": {"input": {}}},
            {"event": "on_tool_end", "name": identity_tool, "run_id": "tool-1", "data": {"output": "{}"}},
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Your email is mara.beck@example.com.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "internal_function" if name == identity_tool else "mcp_tool")
    monkeypatch.setattr(
        app_main,
        "_internal_tool_access_control",
        lambda name: InternalToolAccessControl(access_control_enabled=True, access_class_override="non-cacheable")
        if name == identity_tool
        else InternalToolAccessControl(),
    )

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What email do you have on file for me?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert not cache_runtime.store_calls
    skip_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache write skip")
    assert skip_result["payload"]["result"] == "skip"
    assert skip_result["payload"]["reason"] == "non-cacheable provenance"


@pytest.mark.asyncio
async def test_cs_event_stream_writes_public_cache_for_shared_flight_status(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None)
    flight_tool = "filter_operatingflight_by_flight_number"
    agent = FakeStreamingAgent(
        [
            {"event": "on_tool_start", "name": flight_tool, "run_id": "tool-1", "data": {"input": {"value": "ZX018"}}},
            {"event": "on_tool_end", "name": flight_tool, "run_id": "tool-1", "data": {"output": "{}"}},
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="ZX018 is on time.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "mcp_tool")

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What is the status of ZX018 today?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert cache_runtime.store_calls
    store_call = cache_runtime.store_calls[0]
    assert store_call["access_class"] == "public"
    assert store_call["group_id"] is None
    write_event = next(event for event in events if event["type"] == "tool-call" and event["toolName"] == "Semantic cache write")
    assert write_event["payload"]["resolvedAccessClass"] == "public"
    assert write_event["payload"]["cacheGroupId"] is None


@pytest.mark.asyncio
async def test_cs_event_stream_skips_cache_write_when_cacheable_tool_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None)
    flight_tool = "filter_operatingflight_by_flight_number"
    agent = FakeStreamingAgent(
        [
            {"event": "on_tool_start", "name": flight_tool, "run_id": "tool-1", "data": {"input": {"value": "ZX018"}}},
            {"event": "on_tool_end", "name": flight_tool, "run_id": "tool-1", "data": {"output": json.dumps({"error": "backend unavailable"})}},
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="I could not verify ZX018 right now.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "mcp_tool")

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What is the status of ZX018 today?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert not cache_runtime.store_calls
    skip_result = next(event for event in events if event["type"] == "tool-result" and event["toolName"] == "Semantic cache write skip")
    assert skip_result["payload"]["reason"] == "non-cacheable provenance"
    skip_call = next(event for event in events if event["type"] == "tool-call" and event["toolName"] == "Semantic cache write skip")
    assert skip_call["payload"]["provenanceSummary"]["nonCacheable"] == [f"{flight_tool}:error"]


@pytest.mark.asyncio
async def test_cs_event_stream_continues_when_cache_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None, store_error=RuntimeError("cache unavailable"))
    tier_context_tool = "get_current_service_tier_context"
    agent = FakeStreamingAgent(
        [
            {"event": "on_tool_start", "name": tier_context_tool, "run_id": "tool-1", "data": {"input": {}}},
            {"event": "on_tool_end", "name": tier_context_tool, "run_id": "tool-1", "data": {"output": "{}"}},
            {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Tier guidance without cache write.", tool_calls=[])}},
        ],
        messages=[],
    )

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "internal_function" if name == tier_context_tool else "mcp_tool")
    monkeypatch.setattr(
        app_main,
        "_internal_tool_access_control",
        lambda name: InternalToolAccessControl(access_control_enabled=True, access_class_override="group")
        if name == tier_context_tool
        else InternalToolAccessControl(),
    )

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="What help do I usually get after a cancellation?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    events = decode_sse(chunks)

    assert any(event["type"] == "text-delta" and event["delta"] == "Tier guidance without cache write." for event in events)
    assert not any(event["type"] == "tool-call" and event["toolName"] == "Semantic cache write" for event in events)


@pytest.mark.asyncio
async def test_cs_event_stream_skips_cache_write_for_non_cacheable_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime(hit=None)
    events = [
        {"event": "on_tool_start", "name": "filter_booking_by_customer_id", "run_id": "tool-1", "data": {"input": {"customer_id": "AIRCUST_001"}}},
        {"event": "on_tool_end", "name": "filter_booking_by_customer_id", "run_id": "tool-1", "data": {"output": "{}"}},
        {"event": "on_chat_model_stream", "run_id": "llm-1", "data": {"chunk": SimpleNamespace(content="Your booking was disrupted.", tool_calls=[])}},
    ]
    agent = FakeStreamingAgent(events, messages=[])

    async def fake_get_agent():
        return agent

    monkeypatch.setattr(app_main, "domain", AIRLINE_SUPPORT_DOMAIN)
    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "get_agent", fake_get_agent)
    monkeypatch.setattr(app_main, "_tool_kind", lambda name: "mcp_tool")

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="My flight was disrupted. What happened?")],
        demo_user_id="AIRCUST_001",
    )
    chunks = [chunk async for chunk in app_main.cs_event_stream(request)]
    decoded = decode_sse(chunks)

    assert not cache_runtime.store_calls
    skip_result = next(event for event in decoded if event["type"] == "tool-result" and event["toolName"] == "Semantic cache write skip")
    assert skip_result["payload"]["result"] == "skip"
    assert skip_result["payload"]["reason"] == "non-cacheable provenance"


@pytest.mark.asyncio
async def test_shutdown_resources_closes_async_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_runtime = FakeSemanticCacheRuntime()
    checkpointer = FakeCheckpointer()

    monkeypatch.setattr(app_main, "semantic_cache_service", cache_runtime)
    monkeypatch.setattr(app_main, "_cleanup_process_resources", lambda: None)
    monkeypatch.setattr(app_main, "_checkpointer", checkpointer)

    await app_main.shutdown_resources()

    assert cache_runtime.closed is True
    assert checkpointer.exited is True


@pytest.mark.parametrize(
    ("flags", "expected_class", "expected_reason"),
    [
        ({"public": True, "group": False, "non_cacheable": False}, "public", "public provenance"),
        ({"public": True, "group": True, "non_cacheable": False}, "group", "group provenance"),
        ({"public": False, "group": False, "non_cacheable": True}, None, "non-cacheable provenance"),
        ({"public": False, "group": False, "non_cacheable": False}, None, "no cacheable provenance"),
    ],
)
def test_semantic_cache_service_resolves_store_access(flags, expected_class, expected_reason) -> None:
    service = SemanticCacheService(FakeSettings(), AIRLINE_SUPPORT_DOMAIN)
    resolved_class, reason = service.resolve_store_access(
        saw_public=flags["public"],
        saw_group=flags["group"],
        saw_non_cacheable=flags["non_cacheable"],
    )
    assert resolved_class == expected_class
    assert reason == expected_reason
