"""Meeting-intel entity specs. Redis key prefixes must match the RDI job map."""

from __future__ import annotations

from backend.app.core.domain_schema import (
    EntitySpec,
    FieldSpec,
    RelationshipSpec,
    entity_by_class,
    entity_by_file,
)

# Prefix map (also documented in domains/meeting-intel/rdi/README.md):
# project: person: meeting: participant: transcript: decision: action: risk: dependency: agenda:

_VECTOR = dict(index="vector", vector_dim=1536, distance_metric="cosine", default_factory="list")

ENTITY_SPECS: tuple[EntitySpec, ...] = (
    EntitySpec(
        class_name="Project",
        redis_key_template="project:{project_id}",
        file_name="projects.jsonl",
        id_field="project_id",
        fields=(
            FieldSpec("project_id", "str", "Project identifier", is_key_component=True),
            FieldSpec("name", "str", "Project name", index="text", weight=2.0),
            FieldSpec("status", "str", "Status: planned, in_progress, at_risk, blocked, done", index="tag"),
            FieldSpec("team", "str", "Owning team", index="tag"),
            FieldSpec("lead_person_id", "str", "Engineering or PM lead", index="tag"),
            FieldSpec("target_date", "str", "ISO target date", index="tag", sortable=True),
            FieldSpec("summary", "str", "One-line project summary", index="text"),
        ),
        relationships=(
            RelationshipSpec("lead", "Project lead", "lead_person_id", "Person"),
            RelationshipSpec("meetings", "Meetings for this project", "project_id", "list[Meeting]"),
            RelationshipSpec(
                "dependencies",
                "What this project depends on (single hop)",
                "project_id",
                "list[ProjectDependency]",
            ),
        ),
    ),
    EntitySpec(
        class_name="Person",
        redis_key_template="person:{person_id}",
        file_name="people.jsonl",
        id_field="person_id",
        fields=(
            FieldSpec("person_id", "str", "Person identifier", is_key_component=True),
            FieldSpec("name", "str", "Full name", index="text", weight=2.0),
            FieldSpec("role", "str", "Role: pm, eng_lead, engineer, exec", index="tag"),
            FieldSpec("team", "str", "Team", index="tag"),
            FieldSpec("email", "str", "Email", index="text", no_stem=True),
            FieldSpec("access_role", "str", "Visibility role: team or leadership", index="tag"),
        ),
    ),
    EntitySpec(
        class_name="Meeting",
        redis_key_template="meeting:{meeting_id}",
        file_name="meetings.jsonl",
        id_field="meeting_id",
        fields=(
            FieldSpec("meeting_id", "str", "Meeting identifier", is_key_component=True),
            FieldSpec("project_id", "str", "Primary project", index="tag"),
            FieldSpec("title", "str", "Meeting title", index="text", weight=2.0),
            FieldSpec("meeting_date", "str", "ISO date", index="tag", sortable=True),
            FieldSpec("kind", "str", "Kind: sync, steering, retro", index="tag"),
            FieldSpec("status", "str", "Status: held, upcoming", index="tag"),
            FieldSpec("summary", "str", "Meeting summary", index="text", weight=1.5),
            FieldSpec("visibility", "str", "ACL: team, leadership, all", index="tag"),
            FieldSpec(
                "summary_embedding",
                "list[float]",
                "Vector embedding of the meeting summary (sidecar; RDI does not write this field)",
                **_VECTOR,
            ),
        ),
        relationships=(
            RelationshipSpec("project", "Primary project", "project_id", "Project"),
            RelationshipSpec("participants", "Who attended", "meeting_id", "list[MeetingParticipant]"),
            RelationshipSpec("transcripts", "Transcript segments", "meeting_id", "list[TranscriptSegment]"),
            RelationshipSpec("decisions", "Decisions from this meeting", "meeting_id", "list[Decision]"),
            RelationshipSpec("action_items", "Actions from this meeting", "meeting_id", "list[ActionItem]"),
            RelationshipSpec("risks", "Risks raised here", "meeting_id", "list[Risk]"),
            RelationshipSpec("agendas", "Agenda documents", "meeting_id", "list[Agenda]"),
        ),
    ),
    EntitySpec(
        class_name="MeetingParticipant",
        redis_key_template="participant:{participant_id}",
        file_name="meeting_participants.jsonl",
        id_field="participant_id",
        fields=(
            FieldSpec("participant_id", "str", "Participant row id", is_key_component=True),
            FieldSpec("meeting_id", "str", "Meeting", index="tag"),
            FieldSpec("person_id", "str", "Person", index="tag"),
        ),
        relationships=(
            RelationshipSpec("meeting", "Meeting", "meeting_id", "Meeting"),
            RelationshipSpec("person", "Participant", "person_id", "Person"),
        ),
    ),
    EntitySpec(
        class_name="TranscriptSegment",
        redis_key_template="transcript:{transcript_id}",
        file_name="transcripts.jsonl",
        id_field="transcript_id",
        fields=(
            FieldSpec("transcript_id", "str", "Segment identifier", is_key_component=True),
            FieldSpec("meeting_id", "str", "Parent meeting", index="tag"),
            FieldSpec("segment_id", "str", "Segment id within the meeting", index="tag"),
            FieldSpec("start_ts", "str", "Start offset, HH:MM:SS", index="tag"),
            FieldSpec("speaker_person_id", "str", "Speaker", index="tag"),
            FieldSpec("text", "str", "Spoken text", index="text", weight=2.0),
            FieldSpec(
                "text_embedding",
                "list[float]",
                "Vector embedding of segment text (sidecar; RDI does not write this field)",
                **_VECTOR,
            ),
        ),
        relationships=(
            RelationshipSpec("meeting", "Parent meeting", "meeting_id", "Meeting"),
            RelationshipSpec("speaker", "Speaker", "speaker_person_id", "Person"),
        ),
    ),
    EntitySpec(
        class_name="Decision",
        redis_key_template="decision:{decision_id}",
        file_name="decisions.jsonl",
        id_field="decision_id",
        fields=(
            FieldSpec("decision_id", "str", "Decision identifier", is_key_component=True),
            FieldSpec("meeting_id", "str", "Source meeting", index="tag"),
            FieldSpec("project_id", "str", "Project", index="tag"),
            FieldSpec("text", "str", "Decision text", index="text", weight=2.0),
            FieldSpec("decided_at", "str", "ISO date", index="tag", sortable=True),
            FieldSpec("status", "str", "Status: active or superseded", index="tag"),
            FieldSpec("superseded_by_decision_id", "str | None", "Replacement decision if superseded", index="tag"),
            FieldSpec("source_segment_id", "str | None", "Transcript segment this was extracted from", index="tag"),
            FieldSpec("visibility", "str", "Inherited meeting visibility", index="tag"),
            FieldSpec(
                "text_embedding",
                "list[float]",
                "Vector embedding of the decision text (sidecar; RDI does not write this field)",
                **_VECTOR,
            ),
        ),
        relationships=(
            RelationshipSpec("meeting", "Source meeting", "meeting_id", "Meeting"),
            RelationshipSpec("project", "Project", "project_id", "Project"),
            RelationshipSpec(
                "superseded_by",
                "The current decision that replaced this one",
                "superseded_by_decision_id",
                "Decision | None",
            ),
        ),
    ),
    EntitySpec(
        class_name="ActionItem",
        redis_key_template="action:{action_id}",
        file_name="action_items.jsonl",
        id_field="action_id",
        fields=(
            FieldSpec("action_id", "str", "Action identifier", is_key_component=True),
            FieldSpec("meeting_id", "str", "Source meeting", index="tag"),
            FieldSpec("project_id", "str", "Project", index="tag"),
            FieldSpec("owner_person_id", "str", "Owner", index="tag"),
            FieldSpec("text", "str", "Action description", index="text", weight=2.0),
            FieldSpec("status", "str", "Status: open, done, overdue", index="tag"),
            FieldSpec("due_date", "str", "ISO due date", index="tag", sortable=True),
            FieldSpec("created_at", "str", "ISO created timestamp"),
            FieldSpec("updated_at", "str", "ISO updated timestamp"),
            FieldSpec("source_segment_id", "str | None", "Transcript segment this was extracted from", index="tag"),
            FieldSpec("visibility", "str", "Inherited meeting visibility", index="tag"),
        ),
        relationships=(
            RelationshipSpec("meeting", "Source meeting", "meeting_id", "Meeting"),
            RelationshipSpec("project", "Project", "project_id", "Project"),
            RelationshipSpec("owner", "Owner", "owner_person_id", "Person"),
        ),
    ),
    EntitySpec(
        class_name="Risk",
        redis_key_template="risk:{risk_id}",
        file_name="risks.jsonl",
        id_field="risk_id",
        fields=(
            FieldSpec("risk_id", "str", "Risk identifier", is_key_component=True),
            FieldSpec("project_id", "str", "Project", index="tag"),
            FieldSpec("meeting_id", "str", "Meeting where it was raised", index="tag"),
            FieldSpec("text", "str", "Risk description", index="text", weight=2.0),
            FieldSpec("severity", "str", "Severity: low, med, high", index="tag"),
            FieldSpec("status", "str", "Status: open or mitigated", index="tag"),
            FieldSpec("source_segment_id", "str | None", "Transcript segment this was extracted from", index="tag"),
            FieldSpec("visibility", "str", "Inherited meeting visibility", index="tag"),
            FieldSpec(
                "text_embedding",
                "list[float]",
                "Vector embedding of the risk text (sidecar; RDI does not write this field)",
                **_VECTOR,
            ),
        ),
        relationships=(
            RelationshipSpec("project", "Project", "project_id", "Project"),
            RelationshipSpec("meeting", "Meeting where raised", "meeting_id", "Meeting"),
        ),
    ),
    EntitySpec(
        class_name="ProjectDependency",
        redis_key_template="dependency:{dependency_id}",
        file_name="project_dependencies.jsonl",
        id_field="dependency_id",
        fields=(
            FieldSpec("dependency_id", "str", "Dependency identifier", is_key_component=True),
            FieldSpec("project_id", "str", "Dependent project", index="tag"),
            FieldSpec("depends_on_project_id", "str", "Upstream project", index="tag"),
            FieldSpec("description", "str", "Why this edge exists", index="text"),
            FieldSpec("blocking", "str", "true if this edge currently blocks delivery", index="tag"),
        ),
        relationships=(
            RelationshipSpec("project", "Dependent project", "project_id", "Project"),
            RelationshipSpec("depends_on", "Upstream project", "depends_on_project_id", "Project"),
        ),
    ),
    EntitySpec(
        class_name="Agenda",
        redis_key_template="agenda:{agenda_id}",
        file_name="agendas.jsonl",
        id_field="agenda_id",
        fields=(
            FieldSpec("agenda_id", "str", "Agenda identifier", is_key_component=True),
            FieldSpec("meeting_id", "str", "Upcoming meeting", index="tag"),
            FieldSpec("human_agenda", "str", "Short PM-typed agenda", index="text", weight=1.5),
            FieldSpec("ai_agenda", "str | None", "Agent-generated agenda markdown", index="text"),
            FieldSpec("ai_agenda_sources", "str | None", "JSON list of source ids the agent cited"),
            FieldSpec("generated_at", "str | None", "ISO timestamp when AI agenda was saved"),
            FieldSpec("generated_by", "str | None", "Person or agent that generated the AI agenda", index="tag"),
            FieldSpec("status", "str", "Status: draft or approved", index="tag"),
            FieldSpec("visibility", "str", "Inherited meeting visibility", index="tag"),
        ),
        relationships=(
            RelationshipSpec("meeting", "Upcoming meeting", "meeting_id", "Meeting"),
        ),
    ),
)

ENTITY_BY_FILE = entity_by_file(ENTITY_SPECS)
ENTITY_BY_CLASS = entity_by_class(ENTITY_SPECS)
