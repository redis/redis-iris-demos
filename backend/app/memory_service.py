from __future__ import annotations

from datetime import datetime, timezone
import re
import uuid
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from backend.app.settings import Settings

MessageRole = Literal["USER", "ASSISTANT", "SYSTEM"]
MemoryType = Literal["semantic", "episodic", "message"]

_ACTOR_ID_FALLBACK = "iris-agent"


def _sanitize_id(value: str | None, *, fallback: str) -> str:
    """Normalize IDs to the Memory API format: alphanumeric + hyphen."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (value or "").strip()).strip("-")
    return cleaned or fallback


def sanitize_actor_id(value: str | None, *, fallback: str = _ACTOR_ID_FALLBACK) -> str:
    return _sanitize_id(value, fallback=fallback)


def sanitize_owner_id(value: str | None, *, fallback: str = "unknown-owner") -> str:
    return _sanitize_id(value, fallback=fallback)


def utc_now_iso() -> str:
    """Return an RFC3339 UTC timestamp compatible with current Agent Memory clients."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_memory_items(payload: Any) -> list[dict[str, Any]]:
    """Handle both legacy `memories` and current `items` search payloads."""
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if isinstance(items, list):
        return items
    memories = payload.get("memories")
    if isinstance(memories, list):
        return memories
    return []


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


class MemoryService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._async_client: httpx.AsyncClient | None = None

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        return self._async_client

    async def close(self) -> None:
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None

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
            owner_id=sanitize_owner_id(owner_id or self.settings.memory_owner_id),
            actor_id=sanitize_actor_id(self.settings.memory_actor_id),
            namespace=self.settings.effective_memory_namespace,
            similarity_threshold=float(self.settings.memory_similarity_threshold),
            limit=max(int(self.settings.memory_limit), 1),
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
        if response.status_code < 400:
            return
        if allow_424 and response.status_code == 424:
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Memory API {response.status_code}: {detail}")

    def _build_search_filter(self, connection: MemoryConnection, session_id: str | None = None) -> dict[str, Any]:
        filt: dict[str, Any] = {
            "ownerId": {"eq": connection.owner_id},
            "namespace": {"eq": connection.namespace},
        }
        if session_id:
            filt["sessionId"] = {"eq": session_id}
        return filt

    def search_long_term_memory(
        self,
        *,
        text: str,
        owner_id: str,
        session_id: str | None = None,
        limit: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        connection = self.connection(owner_id=owner_id)
        payload: dict[str, Any] = {
            "filterOp": "all",
            "limit": limit or connection.limit,
            "filter": self._build_search_filter(connection, session_id),
        }

        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.post(
                self._url(connection, "/long-term-memory/search"),
                headers=self._headers(connection),
                json=payload,
            )
        self._raise_for_error(response, allow_424=True)
        body = response.json() if response.content else {}
        return extract_memory_items(body)

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
        payload: dict[str, Any] = {
            "filterOp": "all",
            "limit": limit or connection.limit,
            "filter": self._build_search_filter(connection, session_id),
        }
        client = self._get_async_client()
        response = await client.post(
            self._url(connection, "/long-term-memory/search"),
            headers=self._headers(connection),
            json=payload,
        )
        self._raise_for_error(response, allow_424=True)
        body = response.json() if response.content else {}
        return extract_memory_items(body)

    def create_long_term_memory(
        self,
        *,
        text: str,
        owner_id: str,
        memory_type: MemoryType = "semantic",
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

    def delete_long_term_memory(self, *, owner_id: str, memory_id: str) -> None:
        connection = self.connection(owner_id=owner_id)
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.request(
                "DELETE",
                self._url(connection, "/long-term-memory"),
                headers=self._headers(connection),
                json={"memoryIds": [memory_id]},
            )
        self._raise_for_error(response)

    async def add_session_event(
        self,
        *,
        owner_id: str,
        session_id: str | None,
        actor_id: str,
        role: MessageRole,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connection = self.connection(owner_id=owner_id)
        payload: dict[str, Any] = {
            "actorId": sanitize_actor_id(actor_id, fallback=connection.actor_id),
            "role": role,
            "content": [{"text": text}],
            "createdAt": utc_now_iso(),
            "metadata": metadata or {},
        }
        if session_id:
            payload["sessionId"] = session_id
        client = self._get_async_client()
        response = await client.post(
            self._url(connection, "/session-memory/events"),
            headers=self._headers(connection),
            json=payload,
        )
        self._raise_for_error(response)
        return response.json() if response.content else {}

    async def get_session(self, *, owner_id: str, session_id: str) -> dict[str, Any]:
        connection = self.connection(owner_id=owner_id)
        client = self._get_async_client()
        response = await client.get(
            self._url(connection, f"/session-memory/{session_id}"),
            headers=self._headers(connection),
        )
        self._raise_for_error(response)
        return response.json() if response.content else {}
