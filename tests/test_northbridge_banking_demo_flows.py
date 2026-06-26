import json
from pathlib import Path

import backend.app.main as app_main
from backend.app.core.domain_loader import load_domain


DOMAIN = load_domain("northbridge-banking")

SHARED_GUIDANCE_PAIR = (
    "How do card controls work in the Northbridge app?",
    "How do the card controls in the Northbridge app work?",
)
SUPPORT_GUIDANCE_PAIR = (
    "What help do I usually get if something looks wrong with my card?",
    "What help do I normally get if something looks wrong with my card?",
)


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_shared_product_guidance_flow_populates_public_cache_after_miss(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DOMAIN)

    assert DOMAIN.manifest.seed_langcache == []
    shared_prompts = {
        card.prompt
        for card in DOMAIN.manifest.branding.starter_prompts
        if card.eyebrow == "Public Guidance"
    }
    assert shared_prompts == set(SHARED_GUIDANCE_PAIR)

    scopes = app_main._langcache_attribute_scopes("NBCUST_001")
    assert {"domain": "northbridge-banking", "access_class": "public"} in scopes
    assert {"domain": "northbridge-banking"} not in scopes

    assert app_main._langcache_store_attributes("NBCUST_001", ["public"]) == {
        "domain": "northbridge-banking",
        "access_class": "public",
    }


def test_cohort_support_guidance_flow_populates_group_cache_after_miss(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "domain", DOMAIN)

    support_prompts = {
        card.prompt
        for card in DOMAIN.manifest.branding.starter_prompts
        if card.eyebrow == "Tier-Scoped Support"
    }
    assert support_prompts == set(SUPPORT_GUIDANCE_PAIR)

    assert app_main._langcache_attribute_scopes("NBCUST_001")[0] == {
        "domain": "northbridge-banking",
        "access_class": "group",
        "cache_group_id": "plus_en",
    }
    assert app_main._langcache_attribute_scopes("NBCUST_002")[0] == {
        "domain": "northbridge-banking",
        "access_class": "group",
        "cache_group_id": "plus_en",
    }
    assert app_main._langcache_attribute_scopes("NBCUST_003")[0] == {
        "domain": "northbridge-banking",
        "access_class": "group",
        "cache_group_id": "standard_en",
    }
    assert app_main._langcache_store_attributes("NBCUST_001", ["group", "public"]) == {
        "domain": "northbridge-banking",
        "access_class": "group",
        "cache_group_id": "plus_en",
    }
    assert app_main._langcache_store_attributes("NBCUST_001", ["group", "non-cacheable"]) is None


def test_flagship_card_decline_recovery_flow_is_backed_by_generated_records(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DEMO_USER_ID", raising=False)

    DOMAIN.generate_demo_data(output_dir=tmp_path, update_env_file=False)

    profiles = _jsonl(tmp_path / "customer_profiles.jsonl")
    accounts = _jsonl(tmp_path / "deposit_accounts.jsonl")
    cards = _jsonl(tmp_path / "debit_cards.jsonl")
    authorisations = _jsonl(tmp_path / "card_authorisations.jsonl")
    risk_events = _jsonl(tmp_path / "card_risk_events.jsonl")
    interventions = _jsonl(tmp_path / "card_support_interventions.jsonl")
    options = _jsonl(tmp_path / "card_recovery_options.jsonl")

    profile = next(row for row in profiles if row["customer_id"] == "NBCUST_001")
    account = next(row for row in accounts if row["customer_id"] == profile["customer_id"])
    card = next(row for row in cards if row["account_id"] == account["account_id"])
    authorisation = next(row for row in authorisations if row["card_id"] == card["card_id"])
    risk_event = next(row for row in risk_events if row["linked_authorisation_id"] == authorisation["authorisation_id"])
    intervention = next(row for row in interventions if row["risk_event_id"] == risk_event["risk_event_id"])
    recovery_options = [row for row in options if row["account_id"] == account["account_id"]]

    assert authorisation["merchant_name"] == "Harbor Tech Online"
    assert authorisation["authorisation_status"] == "declined"
    assert card["card_last4"] == "4812"
    assert card["card_status"] == "temporarily_blocked"
    assert intervention["intervention_type"] == "temporary_card_block"
    assert {row["option_code"] for row in recovery_options} == {
        "KEEP_TEMPORARY_BLOCK",
        "UNFREEZE_AFTER_VERIFICATION",
        "ORDER_REPLACEMENT_CARD",
    }

    confirmation = DOMAIN.execute_internal_tool(
        "submit_card_recovery_selection",
        {
            "account_id": account["account_id"],
            "selected_option_code": "Unfreeze after verification",
            "confirm_change": True,
        },
        settings=None,
    )

    assert confirmation["status"] == "confirmed"
    assert confirmation["to_option_code"] == "UNFREEZE_AFTER_VERIFICATION"
