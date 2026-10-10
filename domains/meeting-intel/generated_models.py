"""Generated Context Surface models for the Minutes domain."""

from __future__ import annotations

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class Project(ContextModel):
    """Project entity for the Minutes domain."""

    __redis_key_template__ = "project:{project_id}"

    project_id: str = ContextField(
        description="Project identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Project name",
        index="text",
        weight=2.0,
    )

    status: str = ContextField(
        description="Status: planned, in_progress, at_risk, blocked, done",
        index="tag",
    )

    team: str = ContextField(
        description="Owning team",
        index="tag",
    )

    lead_person_id: str = ContextField(
        description="Engineering or PM lead",
        index="tag",
    )

    target_date: str = ContextField(
        description="ISO target date",
        index="tag",
        sortable=True,
    )

    summary: str = ContextField(
        description="One-line project summary",
        index="text",
    )

    lead: Person = ContextRelationship(
        description="Project lead",
        source_field="lead_person_id",
    )

    meetings: list[Meeting] = ContextRelationship(
        description="Meetings for this project",
        source_field="project_id",
    )

    dependencies: list[ProjectDependency] = ContextRelationship(
        description="What this project depends on (single hop)",
        source_field="project_id",
    )


class Person(ContextModel):
    """Person entity for the Minutes domain."""

    __redis_key_template__ = "person:{person_id}"

    person_id: str = ContextField(
        description="Person identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Full name",
        index="text",
        weight=2.0,
    )

    role: str = ContextField(
        description="Role: pm, eng_lead, engineer, exec",
        index="tag",
    )

    team: str = ContextField(
        description="Team",
        index="tag",
    )

    email: str = ContextField(
        description="Email",
        index="text",
        no_stem=True,
    )

    access_role: str = ContextField(
        description="Visibility role: team or leadership",
        index="tag",
    )


class Meeting(ContextModel):
    """Meeting entity for the Minutes domain."""

    __redis_key_template__ = "meeting:{meeting_id}"

    meeting_id: str = ContextField(
        description="Meeting identifier",
        is_key_component=True,
    )

    project_id: str = ContextField(
        description="Primary project",
        index="tag",
    )

    title: str = ContextField(
        description="Meeting title",
        index="text",
        weight=2.0,
    )

    meeting_date: str = ContextField(
        description="ISO date",
        index="tag",
        sortable=True,
    )

    kind: str = ContextField(
        description="Kind: sync, steering, retro",
        index="tag",
    )

    status: str = ContextField(
        description="Status: held, upcoming",
        index="tag",
    )

    summary: str = ContextField(
        description="Meeting summary",
        index="text",
        weight=1.5,
    )

    visibility: str = ContextField(
        description="ACL: team, leadership, all",
        index="tag",
    )

    summary_embedding: list[float] = ContextField(
        description="Vector embedding of the meeting summary (sidecar; RDI does not write this field)",
        index="vector",
        default_factory=list,
        vector_dim=1536,
        distance_metric="cosine",
    )

    project: Project = ContextRelationship(
        description="Primary project",
        source_field="project_id",
    )

    participants: list[MeetingParticipant] = ContextRelationship(
        description="Who attended",
        source_field="meeting_id",
    )

    transcripts: list[TranscriptSegment] = ContextRelationship(
        description="Transcript segments",
        source_field="meeting_id",
    )

    decisions: list[Decision] = ContextRelationship(
        description="Decisions from this meeting",
        source_field="meeting_id",
    )

    action_items: list[ActionItem] = ContextRelationship(
        description="Actions from this meeting",
        source_field="meeting_id",
    )

    risks: list[Risk] = ContextRelationship(
        description="Risks raised here",
        source_field="meeting_id",
    )

    agendas: list[Agenda] = ContextRelationship(
        description="Agenda documents",
        source_field="meeting_id",
    )


class MeetingParticipant(ContextModel):
    """MeetingParticipant entity for the Minutes domain."""

    __redis_key_template__ = "participant:{participant_id}"

    participant_id: str = ContextField(
        description="Participant row id",
        is_key_component=True,
    )

    meeting_id: str = ContextField(
        description="Meeting",
        index="tag",
    )

    person_id: str = ContextField(
        description="Person",
        index="tag",
    )

    meeting: Meeting = ContextRelationship(
        description="Meeting",
        source_field="meeting_id",
    )

    person: Person = ContextRelationship(
        description="Participant",
        source_field="person_id",
    )


class TranscriptSegment(ContextModel):
    """TranscriptSegment entity for the Minutes domain."""

    __redis_key_template__ = "transcript:{transcript_id}"

    transcript_id: str = ContextField(
        description="Segment identifier",
        is_key_component=True,
    )

    meeting_id: str = ContextField(
        description="Parent meeting",
        index="tag",
    )

    segment_id: str = ContextField(
        description="Segment id within the meeting",
        index="tag",
    )

    start_ts: str = ContextField(
        description="Start offset, HH:MM:SS",
        index="tag",
    )

    speaker_person_id: str = ContextField(
        description="Speaker",
        index="tag",
    )

    text: str = ContextField(
        description="Spoken text",
        index="text",
        weight=2.0,
    )

    text_embedding: list[float] = ContextField(
        description="Vector embedding of segment text (sidecar; RDI does not write this field)",
        index="vector",
        default_factory=list,
        vector_dim=1536,
        distance_metric="cosine",
    )

    meeting: Meeting = ContextRelationship(
        description="Parent meeting",
        source_field="meeting_id",
    )

    speaker: Person = ContextRelationship(
        description="Speaker",
        source_field="speaker_person_id",
    )


class Decision(ContextModel):
    """Decision entity for the Minutes domain."""

    __redis_key_template__ = "decision:{decision_id}"

    decision_id: str = ContextField(
        description="Decision identifier",
        is_key_component=True,
    )

    meeting_id: str = ContextField(
        description="Source meeting",
        index="tag",
    )

    project_id: str = ContextField(
        description="Project",
        index="tag",
    )

    text: str = ContextField(
        description="Decision text",
        index="text",
        weight=2.0,
    )

    decided_at: str = ContextField(
        description="ISO date",
        index="tag",
        sortable=True,
    )

    status: str = ContextField(
        description="Status: active or superseded",
        index="tag",
    )

    superseded_by_decision_id: str | None = ContextField(
        description="Replacement decision if superseded",
        index="tag",
    )

    source_segment_id: str | None = ContextField(
        description="Transcript segment this was extracted from",
        index="tag",
    )

    visibility: str = ContextField(
        description="Inherited meeting visibility",
        index="tag",
    )

    text_embedding: list[float] = ContextField(
        description="Vector embedding of the decision text (sidecar; RDI does not write this field)",
        index="vector",
        default_factory=list,
        vector_dim=1536,
        distance_metric="cosine",
    )

    meeting: Meeting = ContextRelationship(
        description="Source meeting",
        source_field="meeting_id",
    )

    project: Project = ContextRelationship(
        description="Project",
        source_field="project_id",
    )

    superseded_by: Decision | None = ContextRelationship(
        description="The current decision that replaced this one",
        source_field="superseded_by_decision_id",
    )


class ActionItem(ContextModel):
    """ActionItem entity for the Minutes domain."""

    __redis_key_template__ = "action:{action_id}"

    action_id: str = ContextField(
        description="Action identifier",
        is_key_component=True,
    )

    meeting_id: str = ContextField(
        description="Source meeting",
        index="tag",
    )

    project_id: str = ContextField(
        description="Project",
        index="tag",
    )

    owner_person_id: str = ContextField(
        description="Owner",
        index="tag",
    )

    text: str = ContextField(
        description="Action description",
        index="text",
        weight=2.0,
    )

    status: str = ContextField(
        description="Status: open, done, overdue",
        index="tag",
    )

    due_date: str = ContextField(
        description="ISO due date",
        index="tag",
        sortable=True,
    )

    created_at: str = ContextField(
        description="ISO created timestamp",
    )

    updated_at: str = ContextField(
        description="ISO updated timestamp",
    )

    source_segment_id: str | None = ContextField(
        description="Transcript segment this was extracted from",
        index="tag",
    )

    visibility: str = ContextField(
        description="Inherited meeting visibility",
        index="tag",
    )

    meeting: Meeting = ContextRelationship(
        description="Source meeting",
        source_field="meeting_id",
    )

    project: Project = ContextRelationship(
        description="Project",
        source_field="project_id",
    )

    owner: Person = ContextRelationship(
        description="Owner",
        source_field="owner_person_id",
    )


class Risk(ContextModel):
    """Risk entity for the Minutes domain."""

    __redis_key_template__ = "risk:{risk_id}"

    risk_id: str = ContextField(
        description="Risk identifier",
        is_key_component=True,
    )

    project_id: str = ContextField(
        description="Project",
        index="tag",
    )

    meeting_id: str = ContextField(
        description="Meeting where it was raised",
        index="tag",
    )

    text: str = ContextField(
        description="Risk description",
        index="text",
        weight=2.0,
    )

    severity: str = ContextField(
        description="Severity: low, med, high",
        index="tag",
    )

    status: str = ContextField(
        description="Status: open or mitigated",
        index="tag",
    )

    source_segment_id: str | None = ContextField(
        description="Transcript segment this was extracted from",
        index="tag",
    )

    visibility: str = ContextField(
        description="Inherited meeting visibility",
        index="tag",
    )

    text_embedding: list[float] = ContextField(
        description="Vector embedding of the risk text (sidecar; RDI does not write this field)",
        index="vector",
        default_factory=list,
        vector_dim=1536,
        distance_metric="cosine",
    )

    project: Project = ContextRelationship(
        description="Project",
        source_field="project_id",
    )

    meeting: Meeting = ContextRelationship(
        description="Meeting where raised",
        source_field="meeting_id",
    )


class ProjectDependency(ContextModel):
    """ProjectDependency entity for the Minutes domain."""

    __redis_key_template__ = "dependency:{dependency_id}"

    dependency_id: str = ContextField(
        description="Dependency identifier",
        is_key_component=True,
    )

    project_id: str = ContextField(
        description="Dependent project",
        index="tag",
    )

    depends_on_project_id: str = ContextField(
        description="Upstream project",
        index="tag",
    )

    description: str = ContextField(
        description="Why this edge exists",
        index="text",
    )

    blocking: str = ContextField(
        description="true if this edge currently blocks delivery",
        index="tag",
    )

    project: Project = ContextRelationship(
        description="Dependent project",
        source_field="project_id",
    )

    depends_on: Project = ContextRelationship(
        description="Upstream project",
        source_field="depends_on_project_id",
    )


class Agenda(ContextModel):
    """Agenda entity for the Minutes domain."""

    __redis_key_template__ = "agenda:{agenda_id}"

    agenda_id: str = ContextField(
        description="Agenda identifier",
        is_key_component=True,
    )

    meeting_id: str = ContextField(
        description="Upcoming meeting",
        index="tag",
    )

    human_agenda: str = ContextField(
        description="Short PM-typed agenda",
        index="text",
        weight=1.5,
    )

    ai_agenda: str | None = ContextField(
        description="Agent-generated agenda markdown",
        index="text",
    )

    ai_agenda_sources: str | None = ContextField(
        description="JSON list of source ids the agent cited",
    )

    generated_at: str | None = ContextField(
        description="ISO timestamp when AI agenda was saved",
    )

    generated_by: str | None = ContextField(
        description="Person or agent that generated the AI agenda",
        index="tag",
    )

    status: str = ContextField(
        description="Status: draft or approved",
        index="tag",
    )

    visibility: str = ContextField(
        description="Inherited meeting visibility",
        index="tag",
    )

    meeting: Meeting = ContextRelationship(
        description="Upcoming meeting",
        source_field="meeting_id",
    )
