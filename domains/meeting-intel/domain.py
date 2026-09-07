from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from backend.app.core.domain_contract import (
    BrandingConfig,
    DomainManifest,
    GeneratedDataset,
    GuardrailConfig,
    GuardrailRouteConfig,
    IdentityConfig,
    InternalToolDefinition,
    NamespaceConfig,
    PromptCard,
    RagConfig,
    SeedLangCacheEntry,
    SeedMemory,
    ThemeConfig,
)
from backend.app.core.domain_schema import EntitySpec, validate_entity_specs
from backend.app.redis_connection import create_redis_client

ROOT = Path(__file__).resolve().parents[2]
DEMO_PERSON_ID = "person-maya"
DEMO_PERSON_NAME = "Maya Chen"
DEMO_PERSON_EMAIL = "maya.chen@harborline.example"


def _load_local_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(f"meeting_intel_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load meeting-intel module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")
_tools = _load_local_module("tools", "tools.py")

generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS


class MeetingIntelDomain:
    manifest = DomainManifest(
        id="meeting-intel",
        description=(
            "Harborline meeting intelligence: Postgres is the system of record, "
            "RDI syncs rows to Redis, Minutes (the agent) reads via Context Retriever "
            "and writes back through Postgres."
        ),
        generated_models_module="domains.meeting-intel.generated_models",
        generated_models_path="domains/meeting-intel/generated_models.py",
        output_dir="output/meeting-intel",
        data_plane="rdi",
        branding=BrandingConfig(
            app_name="Minutes",
            subtitle="Harborline meeting intelligence",
            hero_title="What should we cover in the next meeting?",
            placeholder_text="Ask about agendas, overdue actions, decisions, or blockers…",
            logo_path="domains/meeting-intel/assets/logo.svg",
            demo_steps=[
                "Draft next week's Platform Migration agenda from overdue work, active decisions, and blockers.",
                "List overdue actions across projects, grouped by owner.",
                "Resolve whether the mobile launch was delayed (latest valid decision).",
                "Walk Customer Portal → Mobile → Platform as two single-hop lookups.",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Agenda",
                    title="Platform Migration sync",
                    prompt="Generate the agenda for next week's Platform Migration sync.",
                ),
                PromptCard(
                    eyebrow="Overdue",
                    title="Actions by owner",
                    prompt="Which action items are overdue across all projects, grouped by owner?",
                ),
                PromptCard(
                    eyebrow="Latest valid",
                    title="Mobile launch delay?",
                    prompt="Did we decide to delay the mobile launch or not?",
                ),
                PromptCard(
                    eyebrow="Dependencies",
                    title="Portal blocker",
                    prompt="What's blocking Customer Portal?",
                ),
            ],
            theme=ThemeConfig(
                bg="#0c1210",
                bg_accent_a="rgba(61, 214, 163, 0.14)",
                bg_accent_b="rgba(245, 200, 66, 0.08)",
                panel="rgba(16, 28, 24, 0.92)",
                panel_strong="rgba(18, 34, 28, 0.97)",
                panel_elevated="rgba(22, 40, 34, 0.95)",
                line="rgba(61, 214, 163, 0.14)",
                line_strong="rgba(245, 200, 66, 0.22)",
                text="#eef7f2",
                muted="#8fa89c",
                soft="#d5e8de",
                accent="#3dd6a3",
                user="#10201a",
                landing_bg="#0c1210",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="meeting-intel",
            dataset_meta_key="meeting-intel:meta:dataset",
            checkpoint_prefix="meeting-intel:checkpoint",
            checkpoint_write_prefix="meeting-intel:checkpoint_write",
            redis_instance_name="Minutes Redis Cloud",
            surface_name="Minutes Context Surface",
            agent_name="Minutes Meeting Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_transcripts",
            status_text="Searching meeting transcripts…",
            generating_text="Drafting from retrieved meeting text…",
            index_name_contains="transcriptsegment",
            vector_field="text_embedding",
            return_fields=["transcript_id", "meeting_id", "segment_id", "speaker_person_id", "text"],
            num_results=6,
            answer_system_prompt=(
                "Answer using only the retrieved transcript segments. Cite transcript_id and "
                "meeting_id. If the segments do not cover the question, say so."
            ),
        ),
        identity=IdentityConfig(
            id_field="person_id",
            default_id=DEMO_PERSON_ID,
            default_name=DEMO_PERSON_NAME,
            default_email=DEMO_PERSON_EMAIL,
            description=(
                "Returns the signed-in Harborline employee: person_id, name, email, team, "
                "and access_role (team or leadership). Call first. Team-role users must not "
                "see leadership-visibility meetings or their derived decisions/actions/risks."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="meeting-intel-guardrail",
            allowed_route_name="in_scope",
            routes=[
                GuardrailRouteConfig(
                    name="in_scope",
                    references=[
                        "generate the agenda for the platform migration sync",
                        "show me that agenda",
                        "show me the saved ai agenda for the platform meeting",
                        "which action items are overdue",
                        "did we decide to delay the mobile launch",
                        "what is blocking customer portal",
                        "and is that blocked",
                        "show me decisions and risks from last steering meeting",
                        "who owns the incomplete platform cutover runbook",
                        "extract follow-ups from this transcript",
                    ],
                    distance_threshold=0.55,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "write me a poem",
                        "what is the weather in tokyo",
                        "how do I cook pasta",
                        "tell me a joke",
                        "help me with my taxes",
                    ],
                    distance_threshold=0.45,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(
                text="Maya prefers agendas grouped by owner, with overdue items listed first.",
                topics=["agenda", "preference"],
            ),
            SeedMemory(
                text="Maya Chen is the engineering lead for Platform Migration (proj-platform).",
                topics=["role", "platform"],
            ),
            SeedMemory(
                text="When preparing a Platform Migration agenda, call out dual-write lag and the unsigned identity SLA because those are why Mobile App is blocked.",
                topics=["platform", "blockers"],
            ),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="Which Platform Migration action items are overdue?",
                response=(
                    "Three Platform Migration actions are overdue and they are why Mobile is blocked: "
                    "[action:act-platform-runbook] cutover runbook (Maya), "
                    "[action:act-platform-dualwrite] dual-write lag under 2s (Priya), "
                    "[action:act-platform-sla] identity service SLA signature (Jordan). "
                    "Source: mtg-2026-09-04-platform."
                ),
                attributes={"domain": "meeting-intel"},
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        return build_system_prompt(mcp_tools=mcp_tools, runtime_config=runtime_config)

    def build_answer_verifier_prompt(self, *, runtime_config: dict[str, Any] | None = None) -> str:
        del runtime_config
        return (
            "Cite meeting_id, decision_id, action_id, and risk_id from tool results. "
            "Never present a superseded decision as current. Never leak leadership-visibility "
            "records to a team-role user. After a write tool, do not claim Redis already has "
            "the row until a Context Retriever read confirms it."
        )

    def describe_tool_trace_step(
        self,
        *,
        tool_name: str,
        payload: Any,
        runtime_config: dict[str, Any] | None = None,
    ) -> str | None:
        del runtime_config
        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in person and their visibility role before reading meetings."
        if tool_name == "save_ai_agenda":
            return "Write the AI agenda to Postgres so RDI can copy it into Redis."
        if tool_name == "create_action_item":
            return "Insert a new action item in Postgres (RDI will sync the Redis key)."
        if tool_name == "update_action_item_status":
            return "Update action status in Postgres for the live CDC beat."
        if tool_name == "extract_from_transcript":
            return "Extract decisions, actions, and risks from transcript segments, then insert in Postgres."
        if tool_name.startswith("filter_projectdependency"):
            return "Single-hop dependency lookup — chain a second call for transitive blockers."
        return None

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        del runtime_config
        return (
            InternalToolDefinition(
                name=self.manifest.identity.tool_name,
                description=self.manifest.identity.description,
            ),
            InternalToolDefinition(
                name="get_current_time",
                description="Current UTC time (ISO 8601). Call before classifying overdue actions.",
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description="Counts of meeting-intel entities currently in Redis.",
            ),
            InternalToolDefinition(
                name="save_ai_agenda",
                description=(
                    "Persist an AI-generated agenda to Postgres for an upcoming meeting. "
                    "RDI copies it to Redis. Inputs: meeting_id, ai_agenda (markdown), "
                    "sources (list of decision/action/risk/meeting ids)."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "ai_agenda": {"type": "string"},
                        "sources": {"type": "array", "items": {"type": "string"}},
                        "generated_by": {"type": "string"},
                    },
                    "required": ["meeting_id", "ai_agenda"],
                },
            ),
            InternalToolDefinition(
                name="create_action_item",
                description="Insert an action item in Postgres. RDI syncs it to Redis.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "project_id": {"type": "string"},
                        "owner_person_id": {"type": "string"},
                        "text": {"type": "string"},
                        "due_date": {"type": "string"},
                    },
                    "required": ["meeting_id", "project_id", "owner_person_id", "text", "due_date"],
                },
            ),
            InternalToolDefinition(
                name="update_action_item_status",
                description="Set an action item status to open, done, or overdue in Postgres.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["action_id", "status"],
                },
            ),
            InternalToolDefinition(
                name="extract_from_transcript",
                description=(
                    "Read transcript segments for meeting_id, extract decisions/actions/risks "
                    "with source_segment_id, validate, and insert into Postgres."
                ),
                input_schema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
        )

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            access_role = (os.getenv("DEMO_USER_ROLE") or "team").strip().lower()
            if access_role not in {"team", "leadership"}:
                access_role = "team"
            return {
                identity.id_field: os.getenv(identity.id_env_var, identity.default_id),
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
                "team": os.getenv("DEMO_USER_TEAM", "Platform"),
                "access_role": access_role,
                "visibility_allowed": ["team", "all"] if access_role == "team" else ["team", "all", "leadership"],
            }
        if tool_name == "get_current_time":
            now = datetime.now(timezone.utc)
            return {"current_time": now.isoformat(), "timezone": "UTC", "today": now.date().isoformat()}
        if tool_name == "dataset_overview":
            client = create_redis_client(settings)
            raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
            if raw:
                data = json.loads(raw)
                return data[0] if isinstance(data, list) else data
            return {"error": "Dataset metadata not found. Run make mi-verify after RDI snapshot."}
        if tool_name == "save_ai_agenda":
            return _tools.save_ai_agenda(arguments, settings)
        if tool_name == "create_action_item":
            return _tools.create_action_item(arguments, settings)
        if tool_name == "update_action_item_status":
            return _tools.update_action_item_status(arguments, settings)
        if tool_name == "extract_from_transcript":
            return _tools.extract_from_transcript(arguments, settings)
        return {"error": f"Unknown tool: {tool_name}"}

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        summary = {
            "projects": len(records.get("Project", [])),
            "people": len(records.get("Person", [])),
            "meetings": len(records.get("Meeting", [])),
            "meeting_participants": len(records.get("MeetingParticipant", [])),
            "transcripts": len(records.get("TranscriptSegment", [])),
            "decisions": len(records.get("Decision", [])),
            "action_items": len(records.get("ActionItem", [])),
            "risks": len(records.get("Risk", [])),
            "project_dependencies": len(records.get("ProjectDependency", [])),
            "agendas": len(records.get("Agenda", [])),
        }
        client = create_redis_client(settings)
        client.execute_command(
            "JSON.SET",
            self.manifest.namespace.dataset_meta_key,
            "$",
            json.dumps(summary, ensure_ascii=False),
        )
        return summary

    def generate_demo_data(
        self,
        *,
        output_dir: Path,
        seed: int | None = None,
        update_env_file: bool = False,
    ) -> GeneratedDataset:
        return generate_demo_data(output_dir=output_dir, seed=seed, update_env_file=update_env_file)

    def validate(self) -> list[str]:
        errors = validate_entity_specs(self.get_entity_specs())
        if not (ROOT / self.manifest.branding.logo_path).exists():
            errors.append(f"Logo file not found: {self.manifest.branding.logo_path}")
        if not self.manifest.branding.starter_prompts:
            errors.append("Branding must define at least one starter prompt")
        jobs_dir = ROOT / "domains" / "meeting-intel" / "rdi" / "jobs"
        expected_jobs = {
            "projects.yaml",
            "people.yaml",
            "meetings.yaml",
            "meeting_participants.yaml",
            "transcripts.yaml",
            "decisions.yaml",
            "action_items.yaml",
            "risks.yaml",
            "project_dependencies.yaml",
            "agendas.yaml",
        }
        present = {path.name for path in jobs_dir.glob("*.yaml")} if jobs_dir.is_dir() else set()
        missing = expected_jobs - present
        if missing:
            errors.append(f"Missing RDI job files: {', '.join(sorted(missing))}")
        schema_path = ROOT / "domains" / "meeting-intel" / "rdi" / "source-db" / "scripts" / "00-schema.sql"
        if not schema_path.exists():
            errors.append("Missing rdi/source-db/scripts/00-schema.sql")
        return errors


DOMAIN = MeetingIntelDomain()
