from types import SimpleNamespace

import backend.app.main as app_main
from backend.app.core.domain_loader import load_domain
from backend.app.request_context import reset_demo_user_id, set_demo_user_id

NORTHBRIDGE_BANKING_DOMAIN = load_domain("northbridge-banking")


def test_northbridge_demo_users_include_shared_group() -> None:
    users = NORTHBRIDGE_BANKING_DOMAIN.get_demo_users()
    plus_en = [user for user in users if user["cache_group_id"] == "plus_en"]
    assert len(plus_en) == 2


def test_northbridge_identity_uses_env_selected_demo_user(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_USER_ID", "NBCUST_002")
    result = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        NORTHBRIDGE_BANKING_DOMAIN.manifest.identity.tool_name,
        {},
        settings=SimpleNamespace(openai_api_key=""),
    )
    assert result["customer_id"] == "NBCUST_002"
    assert result["customer_segment"] == "Plus"
    assert result["cache_group_id"] == "plus_en"


def test_northbridge_identity_uses_request_scoped_demo_user(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_USER_ID", "NBCUST_001")
    token = set_demo_user_id("NBCUST_003")
    try:
        result = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
            NORTHBRIDGE_BANKING_DOMAIN.manifest.identity.tool_name,
            {},
            settings=SimpleNamespace(openai_api_key=""),
        )
    finally:
        reset_demo_user_id(token)

    assert result["customer_id"] == "NBCUST_003"
    assert result["display_name"] == "Casey Alvarez"
    assert result["email"] == "casey.alvarez@example.com"
    assert result["customer_segment"] == "Standard"
    assert result["cache_group_id"] == "standard_en"


def test_northbridge_support_context_includes_tier_specific_routing(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_USER_ID", "NBCUST_001")
    plus = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        "get_current_customer_support_context",
        {},
        settings=SimpleNamespace(openai_api_key=""),
    )
    assert plus["support_plan"] == "Plus Support"
    assert plus["service_permissions"]["priority_support_routing"] is True
    assert "priority support routing" in plus["routing_summary"]

    token = set_demo_user_id("NBCUST_003")
    try:
        standard = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
            "get_current_customer_support_context",
            {},
            settings=SimpleNamespace(openai_api_key=""),
        )
    finally:
        reset_demo_user_id(token)

    assert standard["support_plan"] == "Standard Support"
    assert standard["service_permissions"]["priority_support_routing"] is False
    assert standard["routing_summary"] == "Standard Support uses the standard app and phone support route."


def test_northbridge_submit_card_recovery_selection_validates_inputs(monkeypatch) -> None:
    monkeypatch.delenv("DEMO_USER_ID", raising=False)
    result = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        "submit_card_recovery_selection",
        {
            "account_id": "ACC_001",
            "selected_option_code": "UNFREEZE_AFTER_VERIFICATION",
            "confirm_change": True,
        },
        settings=None,
    )
    assert result["status"] == "confirmed"
    assert result["to_option_code"] == "UNFREEZE_AFTER_VERIFICATION"

    plain_language = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        "submit_card_recovery_selection",
        {
            "account_id": "ACC_001",
            "selected_option_code": "Unfreeze after verification",
            "confirm_change": True,
        },
        settings=None,
    )
    assert plain_language["status"] == "confirmed"
    assert plain_language["to_option_code"] == "UNFREEZE_AFTER_VERIFICATION"

    invalid = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        "submit_card_recovery_selection",
        {
            "account_id": "ACC_003",
            "selected_option_code": "UNFREEZE_AFTER_VERIFICATION",
            "confirm_change": True,
        },
        settings=None,
    )
    assert invalid["status"] == "error"
    assert invalid["error_code"] == "CARD_RECOVERY_ACCOUNT_MISMATCH"

    monkeypatch.setenv("DEMO_USER_ID", "NBCUST_002")
    unauthorized = NORTHBRIDGE_BANKING_DOMAIN.execute_internal_tool(
        "submit_card_recovery_selection",
        {
            "account_id": "ACC_001",
            "selected_option_code": "UNFREEZE_AFTER_VERIFICATION",
            "confirm_change": True,
        },
        settings=None,
    )
    assert unauthorized["status"] == "error"
    assert unauthorized["error_code"] == "CARD_RECOVERY_ACCOUNT_MISMATCH"


def test_northbridge_classifies_mcp_cache_access() -> None:
    assert NORTHBRIDGE_BANKING_DOMAIN.classify_mcp_semantic_cache_access("search_supportguidancedoc_by_text") == "public"
    assert NORTHBRIDGE_BANKING_DOMAIN.classify_mcp_semantic_cache_access("filter_servicestatus_by_service_name") == "public"
    assert (
        NORTHBRIDGE_BANKING_DOMAIN.classify_mcp_semantic_cache_access("filter_customerprofile_by_customer_id")
        == "non-cacheable"
    )
    assert (
        NORTHBRIDGE_BANKING_DOMAIN.classify_mcp_semantic_cache_access("filter_depositaccount_by_customer_id")
        == "non-cacheable"
    )
    assert NORTHBRIDGE_BANKING_DOMAIN.classify_mcp_semantic_cache_access("some_unknown_tool") == "ignored"


def test_northbridge_classifies_internal_cache_access(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", NORTHBRIDGE_BANKING_DOMAIN)

    assert app_main._classify_semantic_cache_access("get_current_customer_support_context") == "group"
    assert app_main._classify_semantic_cache_access("get_current_user_profile") == "non-cacheable"
    assert app_main._classify_semantic_cache_access("submit_card_recovery_selection") == "non-cacheable"
    assert app_main._classify_semantic_cache_access("dataset_overview") == "ignored"


def test_northbridge_langcache_scopes_try_group_before_public(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", NORTHBRIDGE_BANKING_DOMAIN)

    assert app_main._langcache_attribute_scopes("NBCUST_001") == [
        {
            "domain": "northbridge-banking",
            "access_class": "group",
            "cache_group_id": "plus_en",
        },
        {"domain": "northbridge-banking", "access_class": "public"},
    ]


def test_northbridge_langcache_scopes_use_standard_group(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", NORTHBRIDGE_BANKING_DOMAIN)

    assert app_main._langcache_attribute_scopes("NBCUST_003")[0] == {
        "domain": "northbridge-banking",
        "access_class": "group",
        "cache_group_id": "standard_en",
    }
