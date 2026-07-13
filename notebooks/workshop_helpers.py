"""Helpers for the Radish Bank Iris workshop notebooks."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from context_surfaces import UnifiedClient, config as cs_config
from context_surfaces.context_model import ContextModel, export_data_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

NOTEBOOKS_DIR = Path(__file__).resolve().parent
WORKSHOP_DATA_DIR = NOTEBOOKS_DIR / "workshop_data"

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


def _env_str(key: str, default: str = "") -> str:
    return str(os.environ.get(key, default) or "").strip()


def _env_int(key: str, default: int) -> int:
    value = _env_str(key)
    return int(value) if value else default


def _env_float(key: str, default: float) -> float:
    value = _env_str(key)
    return float(value) if value else default


def _env_bool(key: str, default: bool = False) -> bool:
    value = _env_str(key)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    openai_chat_model: str

    redis_host: str
    redis_port: int
    redis_username: str
    redis_password: str
    redis_db: int
    redis_ssl: bool

    ctx_admin_key: str
    ctx_surface_id: str
    mcp_agent_key: str

    memory_api_base_url: str
    memory_store_id: str
    memory_api_key: str
    memory_owner_id: str
    memory_actor_id: str
    memory_namespace: str
    memory_similarity_threshold: float
    memory_limit: int

    langcache_host: str
    langcache_cache_id: str
    langcache_api_key: str
    langcache_threshold: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=_env_str("OPENAI_API_KEY"),
            openai_base_url=_env_str("OPENAI_BASE_URL") or None,
            openai_chat_model=_env_str("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            redis_host=_env_str("REDIS_HOST", "localhost"),
            redis_port=_env_int("REDIS_PORT", 6379),
            redis_username=_env_str("REDIS_USERNAME", "default"),
            redis_password=_env_str("REDIS_PASSWORD"),
            redis_db=_env_int("REDIS_DB", 0),
            redis_ssl=_env_bool("REDIS_SSL", False),
            ctx_admin_key=_env_str("CTX_ADMIN_KEY"),
            ctx_surface_id=_env_str("CTX_SURFACE_ID"),
            mcp_agent_key=_env_str("MCP_AGENT_KEY"),
            memory_api_base_url=_env_str("MEMORY_API_BASE_URL"),
            memory_store_id=_env_str("MEMORY_STORE_ID"),
            memory_api_key=_env_str("MEMORY_API_KEY"),
            memory_owner_id=_env_str("MEMORY_OWNER_ID"),
            memory_actor_id=_env_str("MEMORY_ACTOR_ID", "iris-agent"),
            memory_namespace=_env_str("MEMORY_NAMESPACE"),
            memory_similarity_threshold=_env_float("MEMORY_SIMILARITY_THRESHOLD", 0.7),
            memory_limit=_env_int("MEMORY_LIMIT", 6),
            langcache_host=_env_str("LANGCACHE_HOST"),
            langcache_cache_id=_env_str("LANGCACHE_CACHE_ID"),
            langcache_api_key=_env_str("LANGCACHE_API_KEY"),
            langcache_threshold=_env_float("LANGCACHE_THRESHOLD", 0.82),
        )

    @property
    def effective_memory_namespace(self) -> str:
        return self.memory_namespace or WORKSHOP_MEMORY_NAMESPACE


def get_settings() -> Settings:
    return Settings.from_env()


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


@dataclass(frozen=True)
class MemoryConnection:
    api_base_url: str
    store_id: str
    api_key: str
    owner_id: str
    actor_id: str
    namespace: str
    similarity_threshold: float
    limit: int


class ContextSurfaceService:
    """Barebones Context Surface client used by the workshop notebook."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: UnifiedClient | None = None
        self._tool_cache: list[dict[str, Any]] | None = None

    async def _get_client(self) -> UnifiedClient:
        if self._client is None:
            self._client = UnifiedClient()
            await self._client.__aenter__()
        return self._client

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self.settings.mcp_agent_key:
            return []
        if self._tool_cache is not None:
            return self._tool_cache
        client = await self._get_client()
        tools = await client.list_tools(self.settings.mcp_agent_key)
        self._tool_cache = [tool if isinstance(tool, dict) else tool.model_dump() for tool in tools]
        return self._tool_cache

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        result = await client.query_tool(
            agent_key=self.settings.mcp_agent_key,
            tool_name=tool_name,
            arguments=arguments,
        )
        if isinstance(result, dict):
            content = result.get("content", [])
            if content and isinstance(content, list) and content[0].get("type") == "text":
                text = content[0].get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw_text": text}
            return result
        return {"result": result}


class LangCacheService:
    """Barebones LangCache client used by the workshop notebook."""

    def __init__(self, settings: Settings):
        self._host = settings.langcache_host.rstrip("/")
        self._cache_id = settings.langcache_cache_id
        self._api_key = settings.langcache_api_key
        self._threshold = settings.langcache_threshold
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(self._host and self._cache_id and self._api_key)

    def _base_url(self) -> str:
        return f"{self._host}/v1/caches/{self._cache_id}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def search(self, prompt: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        client = await self._get_client()
        try:
            response = await client.post(
                f"{self._base_url()}/entries/search",
                headers=self._headers(),
                json={
                    "prompt": prompt,
                    "similarityThreshold": self._threshold,
                    "searchStrategies": ["semantic"],
                },
            )
            response.raise_for_status()
            entries = response.json().get("data", [])
        except (httpx.HTTPError, ValueError) as exc:
            print(f"LangCache lookup failed. Continuing as cache miss: {exc}")
            return None
        if not entries:
            return None
        best = entries[0]
        return {
            "hit": True,
            "similarity": best.get("similarity", 0),
            "response": best.get("response", ""),
            "prompt": best.get("prompt", ""),
        }

    async def store(self, prompt: str, response: str, attributes: dict[str, str] | None = None) -> bool:
        if not self.is_configured():
            return False
        body: dict[str, Any] = {"prompt": prompt, "response": response}
        if attributes:
            body["attributes"] = attributes
        client = await self._get_client()
        resp = await client.post(
            f"{self._base_url()}/entries",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return True


def _sanitize_id(value: str | None, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (value or "").strip()).strip("-")
    return cleaned or fallback


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_memory_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if isinstance(items, list):
        return items
    memories = payload.get("memories")
    if isinstance(memories, list):
        return memories
    return []


class MemoryService:
    """Barebones Agent Memory client used by the workshop notebook."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._async_client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(
            self.settings.memory_api_base_url
            and self.settings.memory_store_id
            and self.settings.memory_api_key
        )

    def connection(self, *, owner_id: str | None = None) -> MemoryConnection:
        return MemoryConnection(
            api_base_url=self.settings.memory_api_base_url.rstrip("/"),
            store_id=self.settings.memory_store_id,
            api_key=self.settings.memory_api_key,
            owner_id=_sanitize_id(owner_id or self.settings.memory_owner_id, fallback="unknown-owner"),
            actor_id=_sanitize_id(self.settings.memory_actor_id, fallback="iris-agent"),
            namespace=self.settings.effective_memory_namespace,
            similarity_threshold=self.settings.memory_similarity_threshold,
            limit=max(self.settings.memory_limit, 1),
        )

    def _headers(self, connection: MemoryConnection) -> dict[str, str]:
        api_key = connection.api_key
        if not api_key.lower().startswith(("bearer ", "basic ")):
            api_key = f"Bearer {api_key}"
        return {
            "Authorization": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, connection: MemoryConnection, path: str) -> str:
        return f"{connection.api_base_url}/v1/stores/{connection.store_id}{path}"

    def _raise_for_error(self, response: httpx.Response, *, allow_424: bool = False) -> None:
        if response.status_code < 400 or (allow_424 and response.status_code == 424):
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Memory API {response.status_code}: {detail}")

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        return self._async_client

    def _build_filter(self, connection: MemoryConnection, session_id: str | None = None) -> dict[str, Any]:
        filt: dict[str, Any] = {
            "ownerId": {"eq": connection.owner_id},
            "namespace": {"eq": connection.namespace},
        }
        if session_id:
            filt["sessionId"] = {"eq": session_id}
        return filt

    async def asearch_long_term_memory(
        self,
        *,
        text: str,
        owner_id: str,
        session_id: str | None = None,
        limit: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        connection = self.connection(owner_id=owner_id)
        payload = {
            "text": text,
            "similarityThreshold": similarity_threshold or connection.similarity_threshold,
            "filterOp": "all",
            "limit": limit or connection.limit,
            "filter": self._build_filter(connection, session_id),
        }
        response = await self._get_async_client().post(
            self._url(connection, "/long-term-memory/search"),
            headers=self._headers(connection),
            json=payload,
        )
        self._raise_for_error(response, allow_424=True)
        return _extract_memory_items(response.json() if response.content else {})

    def create_long_term_memory(
        self,
        *,
        text: str,
        owner_id: str,
        memory_type: str = "semantic",
        topics: list[str] | None = None,
        session_id: str | None = None,
        memory_id: str | None = None,
    ) -> dict[str, Any]:
        connection = self.connection(owner_id=owner_id)
        payload = {
            "memories": [
                {
                    "id": memory_id or str(uuid.uuid4()),
                    "text": text,
                    "memoryType": memory_type,
                    "ownerId": connection.owner_id,
                    "sessionId": session_id,
                    "namespace": connection.namespace,
                    "topics": topics or [],
                }
            ]
        }
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.post(
                self._url(connection, "/long-term-memory"),
                headers=self._headers(connection),
                json=payload,
            )
        self._raise_for_error(response)
        return response.json() if response.content else {"ok": True}

    async def add_session_event(
        self,
        *,
        owner_id: str,
        session_id: str | None,
        actor_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connection = self.connection(owner_id=owner_id)
        payload: dict[str, Any] = {
            "actorId": _sanitize_id(actor_id, fallback=connection.actor_id),
            "role": role,
            "content": [{"text": text}],
            "createdAt": _utc_now_iso(),
            "metadata": metadata or {},
        }
        if session_id:
            payload["sessionId"] = session_id
        response = await self._get_async_client().post(
            self._url(connection, "/session-memory/events"),
            headers=self._headers(connection),
            json=payload,
        )
        self._raise_for_error(response)
        return response.json() if response.content else {}

    async def get_session(self, *, owner_id: str, session_id: str) -> dict[str, Any]:
        connection = self.connection(owner_id=owner_id)
        response = await self._get_async_client().get(
            self._url(connection, f"/session-memory/{session_id}"),
            headers=self._headers(connection),
        )
        self._raise_for_error(response)
        return response.json() if response.content else {}


JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def _resolve_json_schema_variant(schema: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    if not isinstance(schema, dict):
        return {"type": "string"}, False

    nullable = False
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null_types = [value for value in schema_type if value != "null"]
        nullable = len(non_null_types) != len(schema_type)
        if len(non_null_types) == 1:
            resolved = dict(schema)
            resolved["type"] = non_null_types[0]
            return resolved, nullable

    for key in ("anyOf", "oneOf"):
        variants = schema.get(key)
        if isinstance(variants, list) and variants:
            non_null_variants = [variant for variant in variants if variant != {"type": "null"}]
            nullable = len(non_null_variants) != len(variants)
            if len(non_null_variants) == 1:
                resolved_variant, variant_nullable = _resolve_json_schema_variant(non_null_variants[0])
                return resolved_variant, nullable or variant_nullable

    return schema, nullable


def _python_type_from_json_schema(schema: dict[str, Any], name: str = "Nested") -> tuple[Any, bool]:
    resolved_schema, nullable = _resolve_json_schema_variant(schema)
    schema_type = resolved_schema.get("type")

    if schema_type == "array":
        items = resolved_schema.get("items")
        if isinstance(items, dict):
            item_type, _ = _python_type_from_json_schema(items, f"{name}Item")
            return list[item_type], nullable
        return list[Any], nullable

    if schema_type == "object":
        properties = resolved_schema.get("properties")
        if isinstance(properties, dict):
            return _pydantic_model_from_json_schema(name, resolved_schema), nullable
        return dict[str, Any], nullable

    return JSON_TYPE_MAP.get(str(schema_type), Any), nullable


def _pydantic_model_from_json_schema(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for prop_name, prop_def in props.items():
        py_type, nullable = _python_type_from_json_schema(prop_def, f"{name}_{prop_name}")
        desc = prop_def.get("description", "")
        field_type = py_type | None if nullable or prop_name not in required else py_type
        if prop_name in required:
            fields[prop_name] = (field_type, Field(description=desc))
        else:
            default = prop_def.get("default")
            fields[prop_name] = (field_type, Field(default=default, description=desc))
    return create_model(f"Schema_{name}", **fields)


def _make_mcp_tool(tool_def: dict[str, Any], cs_service: ContextSurfaceService) -> StructuredTool:
    name = tool_def["name"]
    description = tool_def.get("description", name)
    input_schema = tool_def.get("inputSchema", {"type": "object", "properties": {}})
    args_model = _pydantic_model_from_json_schema(name, input_schema)

    async def fn(**kwargs: Any) -> str:
        clean_args = {key: value for key, value in kwargs.items() if value is not None}
        try:
            result = await cs_service.call_tool(name, clean_args)
            return json.dumps(result or {}, default=str)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return StructuredTool(
        name=name,
        description=description,
        func=lambda **kw: "",
        coroutine=fn,
        args_schema=args_model,
    )


def apply_workshop_config(
    config: dict[str, str],
    *,
    include_defaults: bool = False,
) -> None:
    """Load notebook credentials into ``os.environ`` for the rest of the session."""
    merged = {**WORKSHOP_CONFIG_DEFAULTS, **config} if include_defaults else config
    for key, value in merged.items():
        if value is not None and str(value).strip():
            os.environ[key] = str(value).strip()


def validate_env(config: dict[str, str] | None = None) -> dict[str, str]:
    """Apply ``WORKSHOP_CONFIG`` (if given) and return required credential values."""
    if config is not None:
        apply_workshop_config(config, include_defaults=True)

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


async def _update_surface(settings: Settings, surface_id: str, data_model: dict[str, Any]) -> None:
    api_url = str(cs_config.api_url).rstrip("/")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.put(
            f"{api_url}/api/v1/context-surfaces/{surface_id}",
            headers=_admin_headers(settings.ctx_admin_key),
            json={
                "name": WORKSHOP_SURFACE_NAME,
                "description": "Workshop context surface for Radish Bank demo data",
                "data_model": data_model,
            },
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to update context surface ({response.status_code}): {response.text}"
        )


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
    force_recreate: bool = False,
    update_existing: bool = False,
) -> SetupResult:
    """Create surface and agent key; store IDs in the session environment."""
    validate_env()
    if force_recreate and update_existing:
        raise ValueError("Use either force_recreate=True or update_existing=True, not both.")
    settings = get_settings()

    if not force_recreate and settings.ctx_surface_id and settings.mcp_agent_key:
        if update_existing:
            data_model = _build_data_model(entities)
            await _update_surface(settings, settings.ctx_surface_id, data_model)
        return SetupResult(
            surface_id=settings.ctx_surface_id,
            agent_key=settings.mcp_agent_key,
        )

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

    prior_events = session_events[:-1] if session_events else []

    context_sections: list[str] = []
    short_term_context = _short_term_memory_context(prior_events)
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
    messages.extend(_session_messages(prior_events))
    messages.append(HumanMessage(content=enriched_message))

    tool_names: list[str] = []
    response = await llm_with_tools.ainvoke(messages)
    for _ in range(max_tool_rounds):
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
        response = await llm_with_tools.ainvoke(messages)
    else:
        if response.tool_calls:
            raise RuntimeError(
                f"Tool round limit exceeded after {max_tool_rounds} round(s)"
            )

    final_text = response.content if isinstance(response.content, str) else str(response.content)
    final_text = final_text.strip()
    if not final_text:
        raise RuntimeError("LLM returned an empty assistant response")

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
        session_event_count=len(session_events) + (1 if memory_service.is_configured() else 0),
        tool_calls=tool_names,
        trace=trace,
    )


def print_turn_result(result: ChatTurnResult) -> None:
    print("--- trace ---")
    for line in result.trace:
        print(line)
    print("--- assistant ---")
    print(result.assistant_message)
