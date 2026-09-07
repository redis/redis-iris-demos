import importlib.util
from collections import Counter
from pathlib import Path

from backend.app.core.domain_loader import load_domain
from scripts.generate_models import render


def test_meeting_intel_domain_loads() -> None:
    domain = load_domain("meeting-intel")
    assert domain.manifest.id == "meeting-intel"
    assert domain.manifest.data_plane == "rdi"
    assert domain.manifest.branding.app_name == "Minutes"
    assert domain.manifest.identity.id_field == "person_id"
    assert domain.manifest.identity.default_id == "person-maya"
    assert Path(domain.manifest.branding.logo_path).exists()
    assert domain.manifest.branding.starter_prompts
    assert domain.validate() == []


def test_meeting_intel_internal_tools() -> None:
    domain = load_domain("meeting-intel")
    names = {t.name for t in domain.get_internal_tool_definitions()}
    assert "get_current_user_profile" in names
    assert "get_current_time" in names
    assert "dataset_overview" in names
    assert "save_ai_agenda" in names
    assert "create_action_item" in names
    assert "update_action_item_status" in names
    assert "extract_from_transcript" in names
    profile = domain.execute_internal_tool("get_current_user_profile", {}, settings=None)
    assert profile["person_id"] == "person-maya"
    assert profile["access_role"] == "team"
    clock = domain.execute_internal_tool("get_current_time", {}, settings=None)
    assert "current_time" in clock
    unknown = domain.execute_internal_tool("not_a_tool", {}, settings=None)
    assert "error" in unknown


def test_meeting_intel_prompt_mentions_value_parameter() -> None:
    domain = load_domain("meeting-intel")
    prompt = domain.build_system_prompt(mcp_tools=[])
    assert "value" in prompt
    assert "filter_*" in prompt or "filter_" in prompt
    assert "get_current_user_profile" in prompt
    assert "superseded" in prompt.lower()
    assert "leadership" in prompt.lower()
    assert "single-hop" in prompt.lower() or "single hop" in prompt.lower()


def test_meeting_intel_key_prefixes() -> None:
    domain = load_domain("meeting-intel")
    templates = {spec.class_name: spec.redis_key_template for spec in domain.get_entity_specs()}
    assert templates["Project"].startswith("project:")
    assert templates["Person"].startswith("person:")
    assert templates["Meeting"].startswith("meeting:")
    assert templates["MeetingParticipant"].startswith("participant:")
    assert templates["TranscriptSegment"].startswith("transcript:")
    assert templates["Decision"].startswith("decision:")
    assert templates["ActionItem"].startswith("action:")
    assert templates["Risk"].startswith("risk:")
    assert templates["ProjectDependency"].startswith("dependency:")
    assert templates["Agenda"].startswith("agenda:")


def test_meeting_intel_generate_demo_data(tmp_path: Path) -> None:
    domain = load_domain("meeting-intel")
    result = domain.generate_demo_data(output_dir=tmp_path, update_env_file=False)
    assert result.env_updates["DEMO_USER_ID"] == "person-maya"
    for spec in domain.get_entity_specs():
        assert (tmp_path / spec.file_name).exists(), spec.file_name
    assert result.summary["Person"] == 8
    assert result.summary["Project"] == 5
    assert result.summary["Decision"] >= 20
    assert result.summary["ActionItem"] >= 35
    assert result.summary["Risk"] >= 10
    assert result.summary["Agenda"] == 5
    assert 16 <= result.summary["Meeting"] <= 30
    seed_sql = Path("domains/meeting-intel/rdi/source-db/scripts/01-seed.sql")
    extra_sql = Path("domains/meeting-intel/rdi/source-db/scripts/extra/transcript-05.sql")
    assert seed_sql.exists()
    assert "INSERT INTO people" in seed_sql.read_text()
    assert extra_sql.exists()
    assert "mtg-2026-09-01-pipeline-extra" in extra_sql.read_text()


def test_meeting_intel_seed_story() -> None:
    seed_path = Path("domains/meeting-intel/seed.py")
    spec = importlib.util.spec_from_file_location("meeting_intel_seed", seed_path)
    seed = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(seed)
    statuses = Counter(a["status"] for a in seed.ACTIONS)
    assert statuses["overdue"] >= 6
    assert any(a["action_id"] == "act-platform-runbook" for a in seed.ACTIONS)
    superseded = [d for d in seed.DECISIONS if d["status"] == "superseded"]
    assert len(superseded) >= 3
    keep = next(d for d in seed.DECISIONS if d["decision_id"] == "dec-mobile-keep-aug")
    delay = next(d for d in seed.DECISIONS if d["decision_id"] == "dec-mobile-delay-jul")
    assert keep["status"] == "active"
    assert delay["superseded_by_decision_id"] == "dec-mobile-keep-aug"
    blocking = next(d for d in seed.DEPENDENCIES if d["dependency_id"] == "dep-mobile-platform")
    assert blocking["blocking"] == "true"
    portal = next(d for d in seed.DEPENDENCIES if d["dependency_id"] == "dep-portal-mobile")
    assert portal["depends_on_project_id"] == "proj-mobile"
    leadership = [m for m in seed.MEETINGS if m["visibility"] == "leadership"]
    assert any(m["meeting_id"] == "mtg-2026-08-19-steering" for m in leadership)


def test_meeting_intel_write_tool_validation() -> None:
    tools_path = Path("domains/meeting-intel/tools.py")
    spec = importlib.util.spec_from_file_location("meeting_intel_tools", tools_path)
    tools = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(tools)
    assert "error" in tools.save_ai_agenda({"meeting_id": "", "ai_agenda": "x"}, settings=None)
    assert "error" in tools.save_ai_agenda({"meeting_id": "mtg-x", "ai_agenda": ""}, settings=None)
    assert "error" in tools.create_action_item(
        {
            "meeting_id": "mtg-x",
            "project_id": "proj-x",
            "owner_person_id": "nope",
            "text": "",
            "due_date": "nope",
        },
        settings=None,
    )
    assert "error" in tools.update_action_item_status({"action_id": "act-x", "status": "nope"}, settings=None)


def test_meeting_intel_generated_models_use_typed_relationships() -> None:
    text = render("meeting-intel")
    assert ": Any = ContextRelationship(" not in text
    assert "lead: Person = ContextRelationship(" in text
    assert "dependencies: list[ProjectDependency] = ContextRelationship(" in text


def test_meeting_intel_transcripts_meet_spec_size() -> None:
    spec = importlib.util.spec_from_file_location(
        "meeting_intel_transcripts",
        Path("domains/meeting-intel/transcripts.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    by_meeting: dict[str, list] = {}
    for row in module.TRANSCRIPTS:
        by_meeting.setdefault(row["meeting_id"], []).append(row)
    assert len(by_meeting) == 4
    for meeting_id, rows in by_meeting.items():
        words = sum(len(row["text"].split()) for row in rows)
        assert 20 <= len(rows) <= 40, meeting_id
        assert words >= 800, f"{meeting_id} has {words} words"
