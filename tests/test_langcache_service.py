from types import SimpleNamespace

import pytest

from backend.app.langcache_service import LangCacheService
from scripts.seed_langcache import langcache_attributes_for_domain, should_flush_before_seed


class FakeSemanticCache:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.checks = []
        self.stores = []
        self.cleared = False
        self.disconnected = False

    def check(self, **kwargs):
        self.checks.append(kwargs)
        return self.hits

    def store(self, **kwargs):
        self.stores.append(kwargs)
        return "cache:key"

    def clear(self):
        self.cleared = True

    def disconnect(self):
        self.disconnected = True


def fake_settings():
    return SimpleNamespace(
        demo_domain="northbridge-banking",
        openai_api_key="openai-secret",
        openai_embedding_model="text-embedding-3-small",
        redis_host="redis.example.com",
        redis_port=6379,
        redis_username="default",
        redis_password="secret:with/specials",
        redis_db=0,
        redis_ssl=True,
        langcache_cache_id="cache-123",
        langcache_threshold=0.82,
    )


@pytest.mark.asyncio
async def test_langcache_search_uses_redisvl_filter_expression() -> None:
    service = LangCacheService(fake_settings())
    fake_cache = FakeSemanticCache(
        [
            {
                "vector_distance": 0.09,
                "response": "Cached answer.",
                "prompt": "What is the refund policy?",
            }
        ]
    )
    service._cache = fake_cache

    result = await service.search(
        "Refund policy?",
        attributes={"domain": "northbridge-banking", "access_class": "public"},
    )

    assert result == {
        "hit": True,
        "similarity": 0.91,
        "response": "Cached answer.",
        "prompt": "What is the refund policy?",
    }
    assert fake_cache.checks[0]["prompt"] == "Refund policy?"
    assert fake_cache.checks[0]["num_results"] == 1
    assert str(fake_cache.checks[0]["filter_expression"]) == (
        "(@domain:{northbridge\\-banking} @access_class:{public})"
    )


@pytest.mark.asyncio
async def test_langcache_search_returns_none_on_miss() -> None:
    service = LangCacheService(fake_settings())
    service._cache = FakeSemanticCache([])

    assert await service.search("Refund policy?") is None
    assert service._cache.checks[0]["filter_expression"] is None


@pytest.mark.asyncio
async def test_langcache_store_uses_redisvl_filters() -> None:
    service = LangCacheService(fake_settings())
    fake_cache = FakeSemanticCache([])
    service._cache = fake_cache

    assert await service.store(
        "Prompt",
        "Response",
        attributes={"domain": "northbridge-banking", "access_class": "public"},
    )
    assert fake_cache.stores[0] == {
        "prompt": "Prompt",
        "response": "Response",
        "filters": {"domain": "northbridge-banking", "access_class": "public"},
    }


@pytest.mark.asyncio
async def test_langcache_flush_clears_cache() -> None:
    service = LangCacheService(fake_settings())
    fake_cache = FakeSemanticCache([])
    service._cache = fake_cache

    assert await service.flush()
    assert fake_cache.cleared is True


def test_seed_langcache_attributes_force_active_domain() -> None:
    assert langcache_attributes_for_domain(
        "airline-support",
        {"domain": "wrong", "access_class": "public"},
    ) == {
        "domain": "airline-support",
        "access_class": "public",
    }


def test_langcache_similarity_threshold_converts_to_redisvl_distance() -> None:
    service = LangCacheService(fake_settings())

    assert service._threshold == pytest.approx(0.18)
    assert LangCacheService._distance_threshold(0.82) == pytest.approx(0.18)
    assert LangCacheService._distance_threshold(1.2) == pytest.approx(1.2)


def test_seed_langcache_flush_is_opt_in() -> None:
    assert not should_flush_before_seed("")
    assert not should_flush_before_seed("false")
    assert should_flush_before_seed("1")
    assert should_flush_before_seed("true")
    assert should_flush_before_seed("yes")
