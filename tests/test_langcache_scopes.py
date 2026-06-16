from types import SimpleNamespace

import backend.app.main as app_main


class DomainWithDemoUsers:
    manifest = SimpleNamespace(
        id="airline-support",
        identity=SimpleNamespace(default_id="AIRCUST_001"),
        seed_langcache=[
            SimpleNamespace(
                attributes={
                    "domain": "airline-support",
                    "access_class": "group",
                    "cache_group_id": "senator_en",
                }
            )
        ],
    )

    @staticmethod
    def resolve_demo_user(user_id: str):
        if user_id == "AIRCUST_001":
            return {"cache_group_id": "senator_en"}
        if user_id == "AIRCUST_003":
            return {"cache_group_id": "frequent_en"}
        return None


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
