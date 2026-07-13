from types import SimpleNamespace

import backend.app.main as app_main


class DomainWithDemoUsers:
    manifest = SimpleNamespace(
        id="airline-support",
        identity=SimpleNamespace(default_id="AIRCUST_001", tool_name="get_current_user_profile"),
        seed_langcache=[],
    )

    @staticmethod
    def resolve_demo_user(user_id: str):
        if user_id == "AIRCUST_001":
            return {"cache_group_id": "senator_en"}
        if user_id == "AIRCUST_003":
            return {"cache_group_id": "frequent_en"}
        return None

    @staticmethod
    def classify_prompt_semantic_cache_access(prompt: str):
        if "ZX018" in prompt:
            return "public"
        if "cancellation" in prompt:
            return "group"
        return "non-cacheable"

    @staticmethod
    def classify_mcp_semantic_cache_access(tool_name: str):
        if tool_name.startswith("filter_booking_by_"):
            return "non-cacheable"
        return "ignored"


class DomainWithoutDemoUsers:
    manifest = SimpleNamespace(
        id="reddash",
        identity=SimpleNamespace(default_id="CUST_DEMO_001"),
        seed_langcache=[SimpleNamespace(attributes={"domain": "reddash"})],
    )


def test_langcache_scopes_try_user_group_before_public(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    assert app_main._langcache_attribute_scopes("AIRCUST_001") == [
        {
            "domain": "airline-support",
            "access_class": "group",
            "cache_group_id": "senator_en",
        },
        {"domain": "airline-support", "access_class": "public"},
    ]


def test_langcache_scopes_use_active_users_group(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    assert app_main._langcache_attribute_scopes("AIRCUST_003")[0] == {
        "domain": "airline-support",
        "access_class": "group",
        "cache_group_id": "frequent_en",
    }


def test_langcache_scopes_fall_back_to_default_demo_user_group(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    assert app_main._langcache_attribute_scopes("UNKNOWN_USER")[0] == {
        "domain": "airline-support",
        "access_class": "group",
        "cache_group_id": "senator_en",
    }


def test_langcache_scopes_keep_legacy_domain_fallback(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithoutDemoUsers())

    assert app_main._langcache_attribute_scopes("CUST_DEMO_001") == [
        {"domain": "reddash", "access_class": "public"},
        {"domain": "reddash"},
    ]


def test_langcache_store_attributes_use_prompt_classification(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    assert app_main._langcache_store_attributes("What help do I usually get after a cancellation?", "AIRCUST_003") == {
        "domain": "airline-support",
        "access_class": "group",
        "cache_group_id": "frequent_en",
    }
    assert app_main._langcache_store_attributes("Is ZX018 still on time?", "AIRCUST_001") == {
        "domain": "airline-support",
        "access_class": "public",
    }
    assert app_main._langcache_store_attributes("My flight was disrupted. What happened?", "AIRCUST_001") is None


def test_langcache_store_attributes_skips_when_response_used_noncacheable_tool(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    assert app_main._langcache_store_attributes(
        "What help do I usually get after a cancellation?",
        "AIRCUST_003",
        used_tool_names={"filter_booking_by_customer_id"},
    ) is None


def test_langcache_store_attributes_skips_when_identity_or_memory_tool_used(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DomainWithDemoUsers())

    # The identity tool returns PII, so a group-cacheable prompt must not be
    # stored once the reply consulted it.
    assert app_main._langcache_store_attributes(
        "What help do I usually get after a cancellation?",
        "AIRCUST_003",
        used_tool_names={"get_current_user_profile"},
    ) is None

    # Memory tools are per-user and must likewise keep answers out of the cache.
    assert app_main._langcache_store_attributes(
        "What help do I usually get after a cancellation?",
        "AIRCUST_003",
        used_tool_names={"search_long_term_memory"},
    ) is None
