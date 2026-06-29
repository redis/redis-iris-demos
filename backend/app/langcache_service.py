from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.settings import Settings

log = logging.getLogger("iris.langcache")


class LangCacheService:
    def __init__(self, settings: Settings) -> None:
        self._host = (settings.langcache_host or "").rstrip("/")
        self._cache_id = settings.langcache_cache_id or ""
        self._api_key = settings.langcache_api_key or ""
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
            resp = await client.post(
                f"{self._base_url()}/entries/search",
                headers=self._headers(),
                json={
                    "prompt": prompt,
                    "similarityThreshold": self._threshold,
                    "searchStrategies": ["semantic"],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("data", [])
            if entries:
                best = entries[0]
                log.info(
                    "Cache HIT (similarity=%.3f): %s",
                    best.get("similarity", 0),
                    prompt[:60],
                )
                return {
                    "hit": True,
                    "similarity": best.get("similarity", 0),
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
        client = await self._get_client()
        body: dict[str, Any] = {"prompt": prompt, "response": response}
        if attributes:
            body["attributes"] = attributes
        try:
            resp = await client.post(
                f"{self._base_url()}/entries",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            log.info("Stored cache entry: %s", prompt[:60])
            return True
        except httpx.HTTPStatusError as exc:
            if attributes and exc.response.status_code == 400 and "no attributes are configured" in exc.response.text:
                log.info("LangCache cache has no attribute schema; retrying without attributes")
                return await self.store(prompt, response, attributes=None)
            log.warning("LangCache store failed: %s — body: %s", exc, exc.response.text)
            return False
        except Exception as exc:
            log.warning("LangCache store failed: %s", exc)
            return False

    async def flush(self) -> bool:
        if not self.is_configured():
            return False
        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self._base_url()}/flush",
                headers=self._headers(),
            )
            resp.raise_for_status()
            log.info("Flushed all LangCache entries")
            return True
        except Exception as exc:
            log.warning("LangCache flush failed: %s", exc)
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
