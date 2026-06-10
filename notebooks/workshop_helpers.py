"""Helpers for the Radish Bank Iris workshop notebooks."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from context_surfaces import UnifiedClient, config as cs_config
from context_surfaces.context_model import ContextModel, export_data_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

NOTEBOOKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = NOTEBOOKS_DIR.parent
WORKSHOP_DATA_DIR = NOTEBOOKS_DIR / "workshop_data"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.context_surface_service import ContextSurfaceService  # noqa: E402
from backend.app.langcache_service import LangCacheService  # noqa: E402
from backend.app.langgraph_agent import _make_mcp_tool  # noqa: E402
from backend.app.memory_service import MemoryService  # noqa: E402
from backend.app.settings import Settings, get_settings  # noqa: E402

DEMO_CUSTOMER_ID = "CUST001"
WORKSHOP_SURFACE_NAME = "radish-bank-workshop"
WORKSHOP_AGENT_NAME = "radish-bank-workshop-agent"
WORKSHOP_MEMORY_NAMESPACE = "radish-bank-workshop"

ENTITY_FILES: dict[str, str] = {
    "Customer": "customers.jsonl",
    "Account": "accounts.jsonl",
    "FixedDepositPlan": "fixed_deposit_plans.jsonl",
    "BankDocument": "bank_documents.jsonl",
}

REQUIRED_ENV_KEYS = (
    "OPENAI_API_KEY",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "CTX_ADMIN_KEY",
    "MEMORY_API_BASE_URL",
    "MEMORY_STORE_ID",
    "MEMORY_API_KEY",
    "LANGCACHE_HOST",
    "LANGCACHE_CACHE_ID",
    "LANGCACHE_API_KEY",
)

WORKSHOP_CONFIG_DEFAULTS: dict[str, str] = {
    "OPENAI_CHAT_MODEL": "gpt-4o-mini",
    "REDIS_USERNAME": "default",
    "REDIS_DB": "0",
    "REDIS_SSL": "false",
}

WORKSHOP_SYSTEM_PROMPT = """You are a Radish Bank customer service assistant for demo customer Merv Kwok (customer_id CUST001).

Use MCP tools for balances, accounts, fixed deposit plans, and bank document search.
For filter_* and search_* tools, pass the match as {"value": "..."} — e.g. filter_account_by_customer_id with value CUST001 (never abbreviate to C001).
Fixed deposit plan ids are FD6 and FD12.

When memory context is provided, use it to personalize answers.
Be concise and polite. This is a demo — no long legal disclaimers.
"""

@dataclass
class SetupResult:
    surface_id: str
    agent_key: str


@dataclass
class ChatTurnResult:
    user_message: str
    assistant_message: str
    cache_hit: bool
    cache_similarity: float | None = None
    long_term_memory_count: int = 0
    session_event_count: int = 0
    tool_calls: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def apply_workshop_config(config: dict[str, str]) -> None:
    """Load notebook credentials into ``os.environ`` for the rest of the session."""
    merged = {**WORKSHOP_CONFIG_DEFAULTS, **config}
    for key, value in merged.items():
        if value is not None and str(value).strip():
            os.environ[key] = str(value).strip()


def validate_env(config: dict[str, str] | None = None) -> dict[str, str]:
    """Apply ``WORKSHOP_CONFIG`` (if given) and return required credential values."""
    if config is not None:
        apply_workshop_config(config)

    missing = [key for key in REQUIRED_ENV_KEYS if not (os.environ.get(key) or "").strip()]
    if missing:
        raise RuntimeError(
            "Missing required credentials in WORKSHOP_CONFIG:\n  - "
            + "\n  - ".join(missing)
            + "\n\nPaste your Redis Cloud and OpenAI values into WORKSHOP_CONFIG, then re-run."
        )
    return {key: str(os.environ[key]).strip() for key in REQUIRED_ENV_KEYS}


def _admin_headers(admin_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-API-Key": admin_key,
    }


def _build_data_model(entities: list[type[ContextModel]]) -> dict[str, Any]:
    return export_data_model(
        title=WORKSHOP_SURFACE_NAME,
        description="Radish Bank workshop — Customer, Account, FixedDepositPlan, BankDocument",
        entities=entities,
    )


async def _create_surface(settings: Settings, data_model: dict[str, Any]) -> str:
    api_url = str(cs_config.api_url).rstrip("/")
    body = {
        "name": WORKSHOP_SURFACE_NAME,
        "description": "Workshop context surface for Radish Bank demo data",
        "data_model": data_model,
        "data_source": {
            "type": "redis",
            "connection_config": {
                "addr": f"{settings.redis_host}:{settings.redis_port}",
                "username": settings.redis_username or "default",
                "password": settings.redis_password,
                "db": settings.redis_db,
                "tls_enabled": settings.redis_ssl,
                "pool_size": 10,
                "min_idle_conns": 2,
            },
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/v1/context-surfaces",
            headers=_admin_headers(settings.ctx_admin_key),
            json=body,
        )
    if response.status_code != 201:
        raise RuntimeError(
            f"Failed to create context surface ({response.status_code}): {response.text}"
        )
    return str(response.json()["id"])


async def _create_agent_key(settings: Settings, surface_id: str) -> str:
    api_url = str(cs_config.api_url).rstrip("/")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/v1/context-surfaces/{surface_id}/agent-keys",
            headers=_admin_headers(settings.ctx_admin_key),
            json={"name": WORKSHOP_AGENT_NAME},
        )
    if response.status_code != 201:
        raise RuntimeError(
            f"Failed to create agent key ({response.status_code}): {response.text}"
        )
    return str(response.json()["key"])


def _load_jsonl_records(class_name: str) -> list[dict[str, Any]]:
    file_name = ENTITY_FILES[class_name]
    path = WORKSHOP_DATA_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"Missing workshop data file: {path}")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def seed_workshop_context_data(
    entities: list[type[ContextModel]],
    records: dict[str, list[dict[str, Any]]],
    *,
    settings: Settings | None = None,
    load_bank_documents_from_file: bool = True,
) -> dict[str, int]:
    """Import structured records into the workshop Context Surface."""
    settings = settings or get_settings()
    surface_id = settings.ctx_surface_id
    if not surface_id:
        raise RuntimeError("CTX_SURFACE_ID is missing — run notebook 00 setup first.")
    if not settings.ctx_admin_key:
        raise RuntimeError("CTX_ADMIN_KEY is missing — check WORKSHOP_CONFIG")

    entity_map = {cls.__name__: cls for cls in entities}
    payloads = dict(records)
    if load_bank_documents_from_file and "BankDocument" not in payloads:
        payloads["BankDocument"] = _load_jsonl_records("BankDocument")

    imported: dict[str, int] = {}
    async with UnifiedClient() as client:
        for class_name, rows in payloads.items():
            if class_name not in entity_map:
                raise ValueError(f"Unknown entity {class_name!r} — expected one of {list(entity_map)}")
            model_cls = entity_map[class_name]
            instances = [model_cls(**row) for row in rows]
            result = await client.import_data(
                admin_key=settings.ctx_admin_key,
                context_surface_id=surface_id,
                records=instances,
                on_conflict="overwrite",
                on_error="fail_fast",
            )
            imported[class_name] = result.imported
    return imported


async def run_workshop_setup(
    entities: list[type[ContextModel]],
    *,
    force_recreate: bool = True,
) -> SetupResult:
    """Create surface and agent key; store IDs in the session environment."""
    validate_env()
    settings = get_settings()

    if force_recreate:
        apply_workshop_config(
            {
                "CTX_SURFACE_ID": "",
                "MCP_AGENT_KEY": "",
                "MEMORY_NAMESPACE": WORKSHOP_MEMORY_NAMESPACE,
                "MEMORY_OWNER_ID": DEMO_CUSTOMER_ID,
            }
        )
        settings = get_settings()

    data_model = _build_data_model(entities)
    surface_id = await _create_surface(settings, data_model)
    agent_key = await _create_agent_key(settings, surface_id)

    apply_workshop_config(
        {
            "CTX_SURFACE_ID": surface_id,
            "MCP_AGENT_KEY": agent_key,
            "MEMORY_NAMESPACE": WORKSHOP_MEMORY_NAMESPACE,
            "MEMORY_OWNER_ID": DEMO_CUSTOMER_ID,
        }
    )
    return SetupResult(
        surface_id=surface_id,
        agent_key=agent_key,
    )


def init_services(settings: Settings | None = None) -> tuple[ContextSurfaceService, MemoryService, LangCacheService, Settings]:
    settings = settings or get_settings()
    return (
        ContextSurfaceService(settings),
        MemoryService(settings),
        LangCacheService(settings),
        settings,
    )


def _session_event_text(event: dict[str, Any]) -> str:
    content = event.get("content", [])
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("text"):
            parts.append(str(item["text"]))
    return " ".join(parts).strip()


def _short_term_memory_context(events: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for event in events[-6:]:
        text = _session_event_text(event)
        if not text:
            continue
        role = str(event.get("role", "USER")).upper()
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _long_term_memory_context(memories: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for memory in memories[:5]:
        text = str(memory.get("text", "")).strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def _session_messages(events: list[dict[str, Any]]) -> list[Any]:
    messages: list[Any] = []
    for event in events[-8:]:
        text = _session_event_text(event)
        if not text:
            continue
        role = str(event.get("role", "USER")).upper()
        if role == "ASSISTANT":
            messages.append(AIMessage(content=text))
        else:
            messages.append(HumanMessage(content=text))
    return messages


async def _build_mcp_tools(cs_service: ContextSurfaceService) -> list[Any]:
    tool_defs = await cs_service.list_tools()
    return [_make_mcp_tool(tool_def, cs_service) for tool_def in tool_defs]


def _build_llm(settings: Settings) -> ChatOpenAI:
    model_kw: dict[str, Any] = {
        "model": settings.openai_chat_model,
        "temperature": 0.2,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        model_kw["base_url"] = settings.openai_base_url
    return ChatOpenAI(**model_kw)


async def chat_turn(
    message: str,
    *,
    session_id: str,
    cs_service: ContextSurfaceService,
    memory_service: MemoryService,
    langcache_service: LangCacheService,
    settings: Settings,
    owner_id: str = DEMO_CUSTOMER_ID,
    max_tool_rounds: int = 2,
    store_in_langcache: bool = False,
) -> ChatTurnResult:
    """One chat turn: LangCache → session memory → LTM → LLM + MCP tools."""
    trace: list[str] = []
    user_message = message.strip()
    if not user_message:
        raise ValueError("message must not be empty")

    if langcache_service.is_configured():
        cache_result = await langcache_service.search(user_message)
        if cache_result:
            trace.append(
                f"LangCache HIT (similarity={cache_result.get('similarity', 0):.3f})"
            )
            return ChatTurnResult(
                user_message=user_message,
                assistant_message=str(cache_result.get("response", "")),
                cache_hit=True,
                cache_similarity=float(cache_result.get("similarity", 0) or 0),
                trace=trace,
            )
        trace.append("LangCache MISS")

    if memory_service.is_configured():
        await memory_service.add_session_event(
            owner_id=owner_id,
            session_id=session_id,
            actor_id=owner_id,
            role="USER",
            text=user_message,
            metadata={"source": "workshop-notebook"},
        )
        trace.append("Session memory: stored USER event")

    session_events: list[dict[str, Any]] = []
    long_term_memories: list[dict[str, Any]] = []
    if memory_service.is_configured():
        session_payload = await memory_service.get_session(
            owner_id=owner_id,
            session_id=session_id,
        )
        session_events = session_payload.get("events", []) if isinstance(session_payload, dict) else []
        trace.append(f"Session memory: {len(session_events)} event(s) in thread")

        long_term_memories = await memory_service.asearch_long_term_memory(
            text=user_message,
            owner_id=owner_id,
            limit=5,
        )
        trace.append(f"Long-term memory: {len(long_term_memories)} match(es)")

    context_sections: list[str] = []
    short_term_context = _short_term_memory_context(session_events)
    long_term_context = _long_term_memory_context(long_term_memories)
    if short_term_context:
        context_sections.append(f"Short-term memory:\n{short_term_context}")
    if long_term_context:
        context_sections.append(f"Long-term memory:\n{long_term_context}")

    enriched_message = user_message
    if context_sections:
        enriched_message = (
            f"{user_message}\n\nRetrieved memory context:\n" + "\n\n".join(context_sections)
        )

    tool_defs = await cs_service.list_tools()
    tool_list = "\n".join(
        f"- {tool.get('name', 'unknown')}: {tool.get('description', '').strip()}"
        for tool in tool_defs
    )
    system_prompt = WORKSHOP_SYSTEM_PROMPT + f"\n\nAvailable MCP tools:\n{tool_list}\n"

    llm = _build_llm(settings)
    tools = await _build_mcp_tools(cs_service)
    tool_map = {tool.name: tool for tool in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    prior_events = session_events[:-1] if session_events else []
    messages.extend(_session_messages(prior_events))
    messages.append(HumanMessage(content=enriched_message))

    tool_names: list[str] = []
    response: AIMessage | None = None
    for _ in range(max_tool_rounds):
        response = await llm_with_tools.ainvoke(messages)
        if not response.tool_calls:
            break
        messages.append(response)
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_names.append(tool_name)
            trace.append(f"MCP tool call: {tool_name}")
            tool = tool_map[tool_name]
            result = await tool.ainvoke(tool_call["args"])
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    if response is None:
        raise RuntimeError("LLM did not return a response")

    final_text = response.content if isinstance(response.content, str) else str(response.content)
    final_text = final_text.strip()
    if not final_text:
        final_text = "(No assistant text returned.)"

    if memory_service.is_configured() and final_text:
        await memory_service.add_session_event(
            owner_id=owner_id,
            session_id=session_id,
            actor_id="assistant",
            role="ASSISTANT",
            text=final_text,
            metadata={"source": "workshop-notebook"},
        )
        trace.append("Session memory: stored ASSISTANT event")

    if store_in_langcache and langcache_service.is_configured() and final_text:
        stored = await langcache_service.store(user_message, final_text)
        trace.append(f"LangCache store: {'OK' if stored else 'FAILED'}")

    return ChatTurnResult(
        user_message=user_message,
        assistant_message=final_text,
        cache_hit=False,
        long_term_memory_count=len(long_term_memories),
        session_event_count=len(session_events) + (2 if memory_service.is_configured() else 0),
        tool_calls=tool_names,
        trace=trace,
    )


def print_turn_result(result: ChatTurnResult) -> None:
    print("--- trace ---")
    for line in result.trace:
        print(line)
    print("--- assistant ---")
    print(result.assistant_message)
