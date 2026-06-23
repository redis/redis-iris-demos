import json
from pathlib import Path

from backend.app.core.domain_loader import load_domain


def test_northbridge_banking_domain_loads() -> None:
    domain = load_domain("northbridge-banking")
    assert domain.manifest.id == "northbridge-banking"
    assert Path(domain.manifest.branding.logo_path).exists()
    assert domain.manifest.branding.app_name == "Northbridge Bank"
    assert domain.manifest.branding.subtitle == "Banking support assistant"
    assert domain.manifest.branding.demo_steps
    assert domain.manifest.branding.theme.landing_bg
    assert domain.manifest.seed_memories
    assert domain.manifest.seed_langcache == []
    assert [card.title for card in domain.manifest.branding.starter_prompts] == [
        "Card declined",
        "Card issue help",
        "Normal card help",
        "Card controls",
        "App card controls",
        "Current card status",
    ]

    tool_definitions = {tool.name: tool for tool in domain.get_internal_tool_definitions(runtime_config={})}
    assert set(tool_definitions) == {
        "get_current_user_profile",
        "get_current_customer_support_context",
        "submit_card_recovery_selection",
        "get_current_time",
        "dataset_overview",
    }
    submit_schema = tool_definitions["submit_card_recovery_selection"].input_schema
    assert submit_schema["required"] == ["account_id", "selected_option_code", "confirm_change"]

    prompt = domain.build_system_prompt(mcp_tools=[], runtime_config={})
    assert 'single **"value"** parameter' in prompt
    assert "Flagship card issue path" in prompt
    assert "Segment-aware support-guidance path" in prompt
    assert "use get_current_customer_support_context plus shared guidance" in prompt
    assert "Include the returned support_plan and routing_summary" in prompt
    assert "Shared product-guidance path" in prompt
    assert "Northbridge Bank" in prompt
    assert "Barclays" not in prompt
    assert "northbridge_mobile_app" in prompt

    identity = domain.execute_internal_tool("get_current_user_profile", {}, settings=None)
    assert identity["customer_id"] == "NBCUST_001"
    assert identity["profile_reference"] == "NB-CP-001"
    assert identity["customer_segment"] == "Plus"
    assert identity["cache_group_id"] == "plus_en"
    assert identity["service_permissions"]["instant_card_controls"] is True

    support_context = domain.execute_internal_tool("get_current_customer_support_context", {}, settings=None)
    assert support_context["customer_segment"] == "Plus"
    assert support_context["cache_group_id"] == "plus_en"
    assert support_context["routing_summary"] == (
        "Plus Support includes priority support routing and appointment-style follow-up when appropriate."
    )
    assert "customer_id" not in support_context
    assert "email" not in support_context

    demo_users = domain.get_demo_users()
    assert [user for user in demo_users if user["cache_group_id"] == "plus_en"]


def test_northbridge_banking_data_generator_writes_expected_files(tmp_path: Path) -> None:
    domain = load_domain("northbridge-banking")
    result = domain.generate_demo_data(output_dir=tmp_path, update_env_file=False)
    assert result.env_updates["DEMO_USER_ID"] == "NBCUST_001"
    assert result.env_updates["DEMO_USER_NAME"] == "Maya Chen"
    assert result.env_updates["DEMO_USER_EMAIL"] == "maya.chen@example.com"
    assert result.summary["card_recovery_options"] == 3

    for spec in domain.get_entity_specs():
        assert (tmp_path / spec.file_name).exists()

    profile_rows = [
        json.loads(line)
        for line in (tmp_path / "customer_profiles.jsonl").read_text().splitlines()
        if line.strip()
    ]
    account_rows = [
        json.loads(line)
        for line in (tmp_path / "deposit_accounts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    auth_rows = [
        json.loads(line)
        for line in (tmp_path / "card_authorisations.jsonl").read_text().splitlines()
        if line.strip()
    ]
    risk_rows = [
        json.loads(line)
        for line in (tmp_path / "card_risk_events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    intervention_rows = [
        json.loads(line)
        for line in (tmp_path / "card_support_interventions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    option_rows = [
        json.loads(line)
        for line in (tmp_path / "card_recovery_options.jsonl").read_text().splitlines()
        if line.strip()
    ]
    guidance_rows = [
        json.loads(line)
        for line in (tmp_path / "support_guidance_docs.jsonl").read_text().splitlines()
        if line.strip()
    ]
    service_rows = [
        json.loads(line)
        for line in (tmp_path / "service_statuses.jsonl").read_text().splitlines()
        if line.strip()
    ]

    assert any(row["customer_segment"] == "Plus" for row in profile_rows)
    assert any(row["customer_segment"] == "Standard" for row in profile_rows)
    assert any(row["account_id"] == "ACC_001" for row in account_rows)
    assert any(row["merchant_name"] == "Harbor Tech Online" for row in auth_rows)
    assert any(row["linked_authorisation_id"] == "AUTH_001" for row in risk_rows)
    assert any(row["intervention_type"] == "temporary_card_block" for row in intervention_rows)
    assert len(option_rows) == 3
    assert any(row["category"] == "card_controls" for row in guidance_rows)
    assert any(row["category"] == "support_routing" for row in guidance_rows)
    assert any(row["service_name"] == "northbridge_mobile_app" for row in service_rows)

    public_blob = json.dumps(
        {
            "profiles": profile_rows,
            "accounts": account_rows,
            "guidance": guidance_rows,
        }
    )
    lowered = public_blob.lower()
    assert "barclays" not in lowered
    assert "postcode" not in lowered
    assert "sort code" not in lowered
