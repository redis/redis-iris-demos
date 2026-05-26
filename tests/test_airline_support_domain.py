import json
from pathlib import Path

from backend.app.core.domain_loader import load_domain


def test_airline_support_domain_loads() -> None:
    domain = load_domain("airline-support")
    assert domain.manifest.id == "airline-support"
    assert Path(domain.manifest.branding.logo_path).exists()
    assert domain.manifest.branding.app_name == "Aurora Air"
    assert domain.manifest.branding.hero_title == "Aurora Air"
    assert [card.title for card in domain.manifest.branding.starter_prompts] == [
        "Flight ZX018",
        "Delays and cancellations",
        "Rebooking",
        "After-cancellation help",
    ]

    tool_names = {tool.name for tool in domain.get_internal_tool_definitions(runtime_config={})}
    assert tool_names == {
        "get_current_user_profile",
        "get_current_service_tier_context",
        "get_current_time",
        "dataset_overview",
    }

    prompt = domain.build_system_prompt(mcp_tools=[], runtime_config={})
    assert 'single **"value"** parameter' in prompt
    assert "Flagship disruption path" in prompt
    assert "Post-rebooking serviceability path" in prompt
    assert "Shared flight-number status path" in prompt
    assert "Traveller profile backup path" in prompt
    assert "Tier-aware self-service path" in prompt
    assert "get_current_user_profile first" in prompt.lower()
    rag_prompt = domain.manifest.rag.answer_system_prompt
    assert "summarizing the most relevant guidance" in rag_prompt.lower()
    assert "cannot see the traveller's live booking" in rag_prompt

    identity = domain.execute_internal_tool("get_current_user_profile", {}, settings=None)
    assert identity["customer_id"] == "AIRCUST_001"
    assert identity["profile_reference"] == "PROFILE-001"
    assert identity["status_tier"] == "Senator"
    assert identity["cache_group_id"] == "senator_en"
    assert identity["service_permissions"]["operational_alerts"] is True

    tier_context = domain.execute_internal_tool("get_current_service_tier_context", {}, settings=None)
    assert tier_context["status_tier"] == "Senator"
    assert tier_context["cache_group_id"] == "senator_en"
    assert "customer_id" not in tier_context
    assert "email" not in tier_context


def test_airline_support_data_generator_writes_expected_files(tmp_path: Path) -> None:
    domain = load_domain("airline-support")
    result = domain.generate_demo_data(output_dir=tmp_path, update_env_file=False)
    assert result.env_updates["DEMO_USER_ID"] == "AIRCUST_001"
    assert result.env_updates["DEMO_USER_NAME"] == "Mara Beck"
    assert result.env_updates["DEMO_USER_EMAIL"] == "mara.beck@example.com"
    assert result.summary["bookings"] >= 2
    for spec in domain.get_entity_specs():
        assert (tmp_path / spec.file_name).exists()

    profile_rows = [
        json.loads(line)
        for line in (tmp_path / "customer_profiles.jsonl").read_text().splitlines()
        if line.strip()
    ]
    booking_rows = [
        json.loads(line)
        for line in (tmp_path / "bookings.jsonl").read_text().splitlines()
        if line.strip()
    ]
    operating_flight_rows = [
        json.loads(line)
        for line in (tmp_path / "operating_flights.jsonl").read_text().splitlines()
        if line.strip()
    ]
    segment_rows = [
        json.loads(line)
        for line in (tmp_path / "itinerary_segments.jsonl").read_text().splitlines()
        if line.strip()
    ]
    policy_rows = [
        json.loads(line)
        for line in (tmp_path / "travel_policy_docs.jsonl").read_text().splitlines()
        if line.strip()
    ]
    operational_disruption_rows = [
        json.loads(line)
        for line in (tmp_path / "operational_disruptions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    reaccommodation_rows = [
        json.loads(line)
        for line in (tmp_path / "reaccommodation_records.jsonl").read_text().splitlines()
        if line.strip()
    ]

    profile_blob = json.dumps(profile_rows).lower()
    assert "cust_id" not in profile_blob
    assert "mam_card_num" not in profile_blob
    assert "formatted_birth_dt" not in profile_blob

    assert any(row["booking_locator"] == "ZX73QF" for row in booking_rows)
    assert all("journey_summary" not in row for row in booking_rows)
    assert all("current_itinerary_summary" not in row for row in booking_rows)
    assert all("disruption_state" not in row for row in booking_rows)
    assert any(row["operating_status"] == "cancelled" for row in operating_flight_rows)
    assert all("operating_status" not in row for row in segment_rows)
    assert all("estimated_departure" not in row for row in segment_rows)
    assert any(row["segment_role"] == "updated" for row in segment_rows)
    assert any(row["category"] == "disruptions" for row in policy_rows)
    assert any("automatically rebooked" in row["content"].lower() for row in policy_rows)
    assert any(row["category"] == "status_benefits" for row in policy_rows)
    assert operational_disruption_rows[0]["operating_flight_id"] == "OF_001"
    assert "disruption_reason_code" in operational_disruption_rows[0]
    assert "operational_reason" not in operational_disruption_rows[0]
    assert "customer_id" not in operational_disruption_rows[0]
    assert "booking_id" not in operational_disruption_rows[0]
    assert operational_disruption_rows[0]["disrupted_flight_number"] == "ZX402"
    assert operational_disruption_rows[0]["impact_status"] == "cancelled"
    assert reaccommodation_rows[0]["reaccommodation_status"] == "confirmed"
    assert reaccommodation_rows[0]["reaccommodation_reason_code"] == "SAME_DAY_ALT_ASSIGNED"
