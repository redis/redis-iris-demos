from types import SimpleNamespace

import pytest

from backend.app.langcache_service import LangCacheService
from scripts.seed_langcache import langcache_attributes_for_domain, should_flush_before_seed


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload):
        self.payload = payload
        self.posts = []

    async def post(self, url, headers=None, json=None):
        self.posts.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(self.payload)


def fake_settings():
    return SimpleNamespace(
        langcache_host="https://langcache.example.com",
        langcache_cache_id="cache-123",
        langcache_api_key="secret",
        langcache_threshold=0.82,
    )


@pytest.mark.asyncio
async def test_langcache_search_includes_optional_attributes() -> None:
    client = FakeAsyncClient(
        {
            "data": [
                {
                    "similarity": 0.91,
                    "response": "Cached answer.",
                    "prompt": "What is the refund policy?",
                }
            ]
        }
    )
    service = LangCacheService(fake_settings())
    service._client = client

    result = await service.search("Refund policy?", attributes={"domain": "reddash"})

    assert result == {
        "hit": True,
        "similarity": 0.91,
        "response": "Cached answer.",
        "prompt": "What is the refund policy?",
    }
    assert client.posts[0]["json"] == {
        "prompt": "Refund policy?",
        "similarityThreshold": 0.82,
        "searchStrategies": ["semantic"],
        "attributes": {"domain": "reddash"},
    }


@pytest.mark.asyncio
async def test_langcache_search_omits_empty_attributes() -> None:
    client = FakeAsyncClient({"data": []})
    service = LangCacheService(fake_settings())
    service._client = client

    assert await service.search("Refund policy?") is None
    assert "attributes" not in client.posts[0]["json"]


def test_seed_langcache_attributes_force_active_domain() -> None:
    assert langcache_attributes_for_domain(
        "airline-support",
        {"domain": "wrong", "access_class": "public"},
    ) == {
        "domain": "airline-support",
        "access_class": "public",
    }


def test_seed_langcache_flush_is_opt_in() -> None:
    assert not should_flush_before_seed("")
    assert not should_flush_before_seed("false")
    assert should_flush_before_seed("1")
    assert should_flush_before_seed("true")
    assert should_flush_before_seed("yes")
