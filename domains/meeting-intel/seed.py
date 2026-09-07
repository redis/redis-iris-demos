"""Harborline meeting-intel seed. Canonical story lives here; data_generator emits SQL + JSONL."""

from __future__ import annotations

from typing import Any

TODAY = "2026-09-07"

PEOPLE: list[dict[str, Any]] = [
    {"person_id": "person-maya", "name": "Maya Chen", "role": "eng_lead", "team": "Platform", "email": "maya.chen@harborline.example", "access_role": "team"},
    {"person_id": "person-jordan", "name": "Jordan Hale", "role": "pm", "team": "Platform", "email": "jordan.hale@harborline.example", "access_role": "team"},
    {"person_id": "person-priya", "name": "Priya Shah", "role": "engineer", "team": "Platform", "email": "priya.shah@harborline.example", "access_role": "team"},
    {"person_id": "person-alex", "name": "Alex Kim", "role": "pm", "team": "Mobile", "email": "alex.kim@harborline.example", "access_role": "team"},
    {"person_id": "person-sam", "name": "Sam Okonkwo", "role": "eng_lead", "team": "Mobile", "email": "sam.okonkwo@harborline.example", "access_role": "team"},
    {"person_id": "person-riley", "name": "Riley Park", "role": "pm", "team": "Portal", "email": "riley.park@harborline.example", "access_role": "team"},
    {"person_id": "person-chris", "name": "Chris Nguyen", "role": "eng_lead", "team": "Data", "email": "chris.nguyen@harborline.example", "access_role": "team"},
    {"person_id": "person-dana", "name": "Dana Voss", "role": "exec", "team": "Leadership", "email": "dana.voss@harborline.example", "access_role": "leadership"},
]

PROJECTS: list[dict[str, Any]] = [
    {"project_id": "proj-platform", "name": "Platform Migration", "status": "at_risk", "team": "Platform", "lead_person_id": "person-maya", "target_date": "2026-10-15", "summary": "Move identity and orders off the monolith onto services with dual-write."},
    {"project_id": "proj-mobile", "name": "Mobile App Relaunch", "status": "blocked", "team": "Mobile", "lead_person_id": "person-sam", "target_date": "2026-10-15", "summary": "New iOS/Android app that requires the migrated identity platform."},
    {"project_id": "proj-portal", "name": "Customer Portal", "status": "in_progress", "team": "Portal", "lead_person_id": "person-riley", "target_date": "2026-12-01", "summary": "Self-serve portal that embeds the new mobile session model."},
    {"project_id": "proj-pipeline", "name": "Data Pipeline Modernization", "status": "in_progress", "team": "Data", "lead_person_id": "person-chris", "target_date": "2026-10-30", "summary": "Replace nightly batch extracts with streaming CDC into the warehouse."},
    {"project_id": "proj-compliance", "name": "Compliance Audit", "status": "planned", "team": "Risk", "lead_person_id": "person-jordan", "target_date": "2026-11-15", "summary": "SOC2 evidence pack that depends on the new pipeline lineage."},
]

DEPENDENCIES: list[dict[str, Any]] = [
    {
        "dependency_id": "dep-portal-mobile",
        "project_id": "proj-portal",
        "depends_on_project_id": "proj-mobile",
        "description": "Portal login and session refresh reuse the relaunch mobile auth SDK.",
        "blocking": "false",
    },
    {
        "dependency_id": "dep-mobile-platform",
        "project_id": "proj-mobile",
        "depends_on_project_id": "proj-platform",
        "description": "Mobile cannot ship until identity dual-write is stable and the SLA is signed.",
        "blocking": "true",
    },
    {
        "dependency_id": "dep-compliance-pipeline",
        "project_id": "proj-compliance",
        "depends_on_project_id": "proj-pipeline",
        "description": "Audit evidence requires end-to-end lineage from the modernized pipeline.",
        "blocking": "false",
    },
]


def _mtg(
    meeting_id: str,
    project_id: str,
    title: str,
    meeting_date: str,
    kind: str,
    status: str,
    summary: str,
    visibility: str,
) -> dict[str, Any]:
    return {
        "meeting_id": meeting_id,
        "project_id": project_id,
        "title": title,
        "meeting_date": meeting_date,
        "kind": kind,
        "status": status,
        "summary": summary,
        "visibility": visibility,
    }


MEETINGS: list[dict[str, Any]] = [
    _mtg("mtg-2026-07-02-platform", "proj-platform", "Platform weekly", "2026-07-02", "sync", "held", "Chose Auth0 as the interim identity provider for dual-write.", "team"),
    _mtg("mtg-2026-07-16-platform", "proj-platform", "Platform weekly", "2026-07-16", "sync", "held", "Froze schema changes on the orders service until dual-write lag is under 2s.", "team"),
    _mtg("mtg-2026-07-30-platform", "proj-platform", "Platform weekly", "2026-07-30", "sync", "held", "Lag still 8s. Runbook drafting started. Identity SLA not yet with legal.", "team"),
    _mtg("mtg-2026-08-13-platform", "proj-platform", "Platform weekly", "2026-08-13", "sync", "held", "Unfroze orders schema. Auth0 decision reversed in favor of in-house identity.", "team"),
    _mtg("mtg-2026-08-27-platform", "proj-platform", "Platform weekly", "2026-08-27", "sync", "held", "Cutover dry-run slipped. Dual-write still 4s p95.", "team"),
    _mtg("mtg-2026-09-04-platform", "proj-platform", "Platform weekly", "2026-09-04", "sync", "held", "Runbook incomplete, dual-write lag, unsigned SLA. These three items block Mobile.", "team"),
    _mtg("mtg-2026-07-08-mobile", "proj-mobile", "Mobile weekly", "2026-07-08", "sync", "held", "Team decided to delay the mobile launch to November to wait on platform.", "team"),
    _mtg("mtg-2026-07-22-mobile", "proj-mobile", "Mobile weekly", "2026-07-22", "sync", "held", "Store listing copy locked. Still assuming a November date.", "team"),
    _mtg("mtg-2026-08-12-mobile", "proj-mobile", "Mobile weekly", "2026-08-12", "sync", "held", "Reversed the delay: keep the October 15 launch and pressure platform for dual-write.", "team"),
    _mtg("mtg-2026-09-03-mobile", "proj-mobile", "Mobile weekly", "2026-09-03", "sync", "held", "Blocked on platform identity. Feature flags ready; cannot enable login.", "team"),
    _mtg("mtg-2026-07-14-portal", "proj-portal", "Portal weekly", "2026-07-14", "sync", "held", "Information architecture for account settings approved.", "team"),
    _mtg("mtg-2026-08-11-portal", "proj-portal", "Portal weekly", "2026-08-11", "sync", "held", "Will embed mobile session SDK; depends on relaunch.", "team"),
    _mtg("mtg-2026-08-25-portal", "proj-portal", "Portal weekly", "2026-08-25", "sync", "held", "Billing widgets mocked. Still waiting on mobile auth.", "team"),
    _mtg("mtg-2026-07-09-pipeline", "proj-pipeline", "Pipeline weekly", "2026-07-09", "sync", "held", "Picked Debezium for CDC. First table: orders.", "team"),
    _mtg("mtg-2026-08-06-pipeline", "proj-pipeline", "Pipeline weekly", "2026-08-06", "sync", "held", "Orders stream in staging. Lineage catalog not started.", "team"),
    _mtg("mtg-2026-08-20-pipeline", "proj-pipeline", "Pipeline weekly", "2026-08-20", "sync", "held", "Warehouse slots reserved. PII classification remaining.", "team"),
    _mtg("mtg-2026-08-28-compliance", "proj-compliance", "Compliance kickoff", "2026-08-28", "sync", "held", "Scoped SOC2 evidence to pipeline lineage plus access logs.", "team"),
    _mtg("mtg-2026-07-15-steering", "proj-platform", "Q3 delivery steering", "2026-07-15", "steering", "held", "Cross-project review: Portal depends on Mobile depends on Platform. No budget discussion.", "all"),
    _mtg("mtg-2026-08-19-steering", "proj-platform", "Leadership steering", "2026-08-19", "steering", "held", "Confidential: hiring freeze through October and a possible acqui-hire of Nimbus Auth. Not for team agendas.", "leadership"),
    _mtg("mtg-2026-09-02-steering", "proj-platform", "Cross-project steering", "2026-09-02", "steering", "held", "Confirmed 2-hop chain Portal→Mobile→Platform. Mobile blocked on platform overdue work.", "all"),
    _mtg("mtg-2026-09-09-platform", "proj-platform", "Platform weekly", "2026-09-09", "sync", "upcoming", "Upcoming: migration status, Q4 dates, hiring coverage.", "team"),
    _mtg("mtg-2026-09-10-mobile", "proj-mobile", "Mobile weekly", "2026-09-10", "sync", "upcoming", "Upcoming: launch date confirmation and platform dependency.", "team"),
    _mtg("mtg-2026-09-10-portal", "proj-portal", "Portal weekly", "2026-09-10", "sync", "upcoming", "Upcoming: session SDK integration plan.", "team"),
    _mtg("mtg-2026-09-11-pipeline", "proj-pipeline", "Pipeline weekly", "2026-09-11", "sync", "upcoming", "Upcoming: PII classification and lineage catalog.", "team"),
    _mtg("mtg-2026-09-11-compliance", "proj-compliance", "Compliance weekly", "2026-09-11", "sync", "upcoming", "Upcoming: evidence inventory vs pipeline dates.", "team"),
]

ATTENDEES: dict[str, list[str]] = {
    "mtg-2026-07-02-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-07-16-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-07-30-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-08-13-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-08-27-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-09-04-platform": ["person-maya", "person-jordan", "person-priya", "person-sam"],
    "mtg-2026-07-08-mobile": ["person-sam", "person-alex", "person-maya"],
    "mtg-2026-07-22-mobile": ["person-sam", "person-alex"],
    "mtg-2026-08-12-mobile": ["person-sam", "person-alex", "person-jordan"],
    "mtg-2026-09-03-mobile": ["person-sam", "person-alex", "person-maya"],
    "mtg-2026-07-14-portal": ["person-riley", "person-alex"],
    "mtg-2026-08-11-portal": ["person-riley", "person-sam"],
    "mtg-2026-08-25-portal": ["person-riley", "person-alex"],
    "mtg-2026-07-09-pipeline": ["person-chris", "person-jordan"],
    "mtg-2026-08-06-pipeline": ["person-chris", "person-priya"],
    "mtg-2026-08-20-pipeline": ["person-chris", "person-jordan"],
    "mtg-2026-08-28-compliance": ["person-jordan", "person-chris", "person-dana"],
    "mtg-2026-07-15-steering": ["person-dana", "person-maya", "person-sam", "person-riley", "person-chris", "person-jordan"],
    "mtg-2026-08-19-steering": ["person-dana", "person-jordan"],
    "mtg-2026-09-02-steering": ["person-dana", "person-maya", "person-sam", "person-riley", "person-chris", "person-alex"],
    "mtg-2026-09-09-platform": ["person-maya", "person-jordan", "person-priya"],
    "mtg-2026-09-10-mobile": ["person-sam", "person-alex"],
    "mtg-2026-09-10-portal": ["person-riley", "person-alex"],
    "mtg-2026-09-11-pipeline": ["person-chris", "person-jordan"],
    "mtg-2026-09-11-compliance": ["person-jordan", "person-chris"],
}

DECISIONS: list[dict[str, Any]] = [
    {"decision_id": "dec-auth0-jul", "meeting_id": "mtg-2026-07-02-platform", "project_id": "proj-platform", "text": "Use Auth0 as the interim identity provider during dual-write.", "decided_at": "2026-07-02", "status": "superseded", "superseded_by_decision_id": "dec-inhouse-aug", "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-inhouse-aug", "meeting_id": "mtg-2026-08-13-platform", "project_id": "proj-platform", "text": "Build in-house identity instead of Auth0; keep dual-write against the new service.", "decided_at": "2026-08-13", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-freeze-jul", "meeting_id": "mtg-2026-07-16-platform", "project_id": "proj-platform", "text": "Freeze orders-service schema changes until dual-write p95 lag is under 2 seconds.", "decided_at": "2026-07-16", "status": "superseded", "superseded_by_decision_id": "dec-unfreeze-aug", "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-unfreeze-aug", "meeting_id": "mtg-2026-08-13-platform", "project_id": "proj-platform", "text": "Lift the orders schema freeze so mobile contract tests can land; lag target stays 2s.", "decided_at": "2026-08-13", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-mobile-delay-jul", "meeting_id": "mtg-2026-07-08-mobile", "project_id": "proj-mobile", "text": "Delay the mobile relaunch to November 12 so platform identity can finish.", "decided_at": "2026-07-08", "status": "superseded", "superseded_by_decision_id": "dec-mobile-keep-aug", "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-mobile-keep-aug", "meeting_id": "mtg-2026-08-12-mobile", "project_id": "proj-mobile", "text": "Do not delay: keep the October 15 mobile launch and treat platform dual-write as a launch blocker to burn down, not a date change.", "decided_at": "2026-08-12", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-debezium-jul", "meeting_id": "mtg-2026-07-09-pipeline", "project_id": "proj-pipeline", "text": "Use Debezium for CDC into the warehouse, starting with the orders table.", "decided_at": "2026-07-09", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-portal-sdk-aug", "meeting_id": "mtg-2026-08-11-portal", "project_id": "proj-portal", "text": "Portal will embed the mobile session SDK rather than a separate web auth stack.", "decided_at": "2026-08-11", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-soc2-scope", "meeting_id": "mtg-2026-08-28-compliance", "project_id": "proj-compliance", "text": "SOC2 evidence is limited to pipeline lineage plus access logs; no extra vendor questionnaires this quarter.", "decided_at": "2026-08-28", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-steer-graph-jul", "meeting_id": "mtg-2026-07-15-steering", "project_id": "proj-platform", "text": "Acknowledge the delivery graph: Customer Portal depends on Mobile, Mobile depends on Platform.", "decided_at": "2026-07-15", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "all"},
    {"decision_id": "dec-lead-freeze", "meeting_id": "mtg-2026-08-19-steering", "project_id": "proj-platform", "text": "Hiring freeze through 31 October except for the identity SRE seat.", "decided_at": "2026-08-19", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-lead-07", "visibility": "leadership"},
    {"decision_id": "dec-lead-nimbus", "meeting_id": "mtg-2026-08-19-steering", "project_id": "proj-platform", "text": "Explore acqui-hire of Nimbus Auth as a fallback if in-house identity slips past October 15.", "decided_at": "2026-08-19", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-lead-12", "visibility": "leadership"},
    {"decision_id": "dec-steer-block-sep", "meeting_id": "mtg-2026-09-02-steering", "project_id": "proj-mobile", "text": "Declare Mobile officially blocked on Platform until dual-write p95 < 2s and the identity SLA is signed.", "decided_at": "2026-09-02", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-steer-11", "visibility": "all"},
    {"decision_id": "dec-keep-oct15-platform", "meeting_id": "mtg-2026-09-04-platform", "project_id": "proj-platform", "text": "Keep Platform cutover target of 15 October; no silent date slip.", "decided_at": "2026-09-04", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-plat-08", "visibility": "team"},
    {"decision_id": "dec-no-partial-login", "meeting_id": "mtg-2026-09-03-mobile", "project_id": "proj-mobile", "text": "Do not ship a partial login on the old monolith; wait for migrated identity.", "decided_at": "2026-09-03", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-mob-09", "visibility": "team"},
    {"decision_id": "dec-feature-flags-on", "meeting_id": "mtg-2026-09-03-mobile", "project_id": "proj-mobile", "text": "Keep feature flags dark until platform identity is green; do not enable store rollout.", "decided_at": "2026-09-03", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-mob-14", "visibility": "team"},
    {"decision_id": "dec-ia-portal", "meeting_id": "mtg-2026-07-14-portal", "project_id": "proj-portal", "text": "Ship account-settings IA as designed; no extra billing tab this quarter.", "decided_at": "2026-07-14", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-orders-first", "meeting_id": "mtg-2026-08-06-pipeline", "project_id": "proj-pipeline", "text": "Orders remains the first warehouse stream; payments wait until PII tags exist.", "decided_at": "2026-08-06", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-pii-before-lineage", "meeting_id": "mtg-2026-08-20-pipeline", "project_id": "proj-pipeline", "text": "Finish PII classification before publishing the lineage catalog to compliance.", "decided_at": "2026-08-20", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-dryrun-required", "meeting_id": "mtg-2026-08-27-platform", "project_id": "proj-platform", "text": "A successful cutover dry-run is required before the October 15 window.", "decided_at": "2026-08-27", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-sam-on-platform-sync", "meeting_id": "mtg-2026-09-04-platform", "project_id": "proj-platform", "text": "Sam joins Platform weekly until the blocking identity work clears.", "decided_at": "2026-09-04", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-plat-18", "visibility": "team"},
    {"decision_id": "dec-portal-wait", "meeting_id": "mtg-2026-08-25-portal", "project_id": "proj-portal", "text": "Portal will not start session integration until Mobile confirms the SDK tag.", "decided_at": "2026-08-25", "status": "active", "superseded_by_decision_id": None, "source_segment_id": None, "visibility": "team"},
    {"decision_id": "dec-steer-no-date-change", "meeting_id": "mtg-2026-09-02-steering", "project_id": "proj-platform", "text": "Do not change October 15 dates in this steering; burn down platform overdues instead.", "decided_at": "2026-09-02", "status": "active", "superseded_by_decision_id": None, "source_segment_id": "seg-steer-16", "visibility": "all"},
]


def _act(
    action_id: str,
    meeting_id: str,
    project_id: str,
    owner: str,
    text: str,
    status: str,
    due: str,
    created: str,
    segment: str | None,
    visibility: str = "team",
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "meeting_id": meeting_id,
        "project_id": project_id,
        "owner_person_id": owner,
        "text": text,
        "status": status,
        "due_date": due,
        "created_at": f"{created}T15:00:00Z",
        "updated_at": f"{created}T15:00:00Z",
        "source_segment_id": segment,
        "visibility": visibility,
    }


ACTIONS: list[dict[str, Any]] = [
    _act("act-platform-runbook", "mtg-2026-09-04-platform", "proj-platform", "person-maya", "Finish the cutover runbook including rollback and dual-write drain steps.", "overdue", "2026-09-01", "2026-08-27", "seg-plat-06"),
    _act("act-platform-dualwrite", "mtg-2026-09-04-platform", "proj-platform", "person-priya", "Bring identity dual-write p95 lag under 2 seconds in staging.", "overdue", "2026-09-02", "2026-08-13", "seg-plat-10"),
    _act("act-platform-sla", "mtg-2026-09-04-platform", "proj-platform", "person-jordan", "Get Legal signature on the identity service SLA.", "overdue", "2026-09-03", "2026-07-30", "seg-plat-14"),
    _act("act-platform-dryrun", "mtg-2026-08-27-platform", "proj-platform", "person-maya", "Schedule the October cutover dry-run with SRE.", "open", "2026-09-12", "2026-08-27", None),
    _act("act-platform-metrics", "mtg-2026-08-13-platform", "proj-platform", "person-priya", "Publish dual-write lag dashboard to #platform.", "done", "2026-08-20", "2026-08-13", None),
    _act("act-platform-auth0-exit", "mtg-2026-08-13-platform", "proj-platform", "person-jordan", "Cancel the Auth0 trial so we do not get billed in September.", "done", "2026-08-18", "2026-08-13", None),
    _act("act-mobile-flags", "mtg-2026-09-03-mobile", "proj-mobile", "person-sam", "Keep login feature flags dark until Maya confirms identity green.", "open", "2026-09-15", "2026-09-03", "seg-mob-14"),
    _act("act-mobile-store", "mtg-2026-09-03-mobile", "proj-mobile", "person-alex", "Hold App Store / Play rollout metadata; do not submit.", "open", "2026-09-16", "2026-09-03", "seg-mob-16"),
    _act("act-mobile-pressure", "mtg-2026-08-12-mobile", "proj-mobile", "person-alex", "Send platform a written blocker note after reversing the delay.", "done", "2026-08-13", "2026-08-12", None),
    _act("act-mobile-copy", "mtg-2026-07-22-mobile", "proj-mobile", "person-alex", "Lock store listing copy for the relaunch.", "done", "2026-07-29", "2026-07-22", None),
    _act("act-portal-sdk", "mtg-2026-08-11-portal", "proj-portal", "person-riley", "Spike embedding the mobile session SDK in the portal shell.", "open", "2026-09-18", "2026-08-11", None),
    _act("act-portal-ia", "mtg-2026-07-14-portal", "proj-portal", "person-riley", "Publish account-settings IA to Figma.", "done", "2026-07-21", "2026-07-14", None),
    _act("act-portal-billing", "mtg-2026-08-25-portal", "proj-portal", "person-riley", "Finish billing widget mocks without wiring live charges.", "done", "2026-09-01", "2026-08-25", None),
    _act("act-pipe-orders", "mtg-2026-07-09-pipeline", "proj-pipeline", "person-chris", "Stand up Debezium on orders in staging.", "done", "2026-07-23", "2026-07-09", None),
    _act("act-pipe-pii", "mtg-2026-08-20-pipeline", "proj-pipeline", "person-chris", "Complete PII classification for orders and payments.", "open", "2026-09-14", "2026-08-20", None),
    _act("act-pipe-lineage", "mtg-2026-08-20-pipeline", "proj-pipeline", "person-jordan", "Draft lineage catalog outline for compliance.", "overdue", "2026-09-01", "2026-08-20", None),
    _act("act-comp-inventory", "mtg-2026-08-28-compliance", "proj-compliance", "person-jordan", "Inventory SOC2 evidence vs pipeline dates.", "open", "2026-09-18", "2026-08-28", None),
    _act("act-lead-sre", "mtg-2026-08-19-steering", "proj-platform", "person-dana", "Open the exception req for the identity SRE seat during the freeze.", "open", "2026-09-10", "2026-08-19", "seg-lead-09", "leadership"),
    _act("act-lead-nimbus", "mtg-2026-08-19-steering", "proj-platform", "person-dana", "NDA pack for Nimbus Auth acqui-hire conversation.", "open", "2026-09-12", "2026-08-19", "seg-lead-14", "leadership"),
    _act("act-steer-comms", "mtg-2026-09-02-steering", "proj-mobile", "person-alex", "Publish a team-readable note that Mobile is blocked on Platform overdues.", "done", "2026-09-04", "2026-09-02", "seg-steer-18"),
    _act("act-plat-old-runbook-draft", "mtg-2026-07-30-platform", "proj-platform", "person-maya", "Start cutover runbook outline.", "done", "2026-08-10", "2026-07-30", None),
    _act("act-plat-legal-intro", "mtg-2026-07-30-platform", "proj-platform", "person-jordan", "Intro Legal to the identity SLA template.", "done", "2026-08-06", "2026-07-30", None),
    _act("act-mobile-old-delay-comms", "mtg-2026-07-08-mobile", "proj-mobile", "person-alex", "Tell marketing the launch moves to November (later reversed).", "done", "2026-07-09", "2026-07-08", None),
    _act("act-pipe-slots", "mtg-2026-08-20-pipeline", "proj-pipeline", "person-chris", "Reserve warehouse slots for the orders stream.", "done", "2026-08-22", "2026-08-20", None),
    _act("act-portal-wait-tag", "mtg-2026-08-25-portal", "proj-portal", "person-riley", "Ping Sam for the mobile SDK tag before starting integration.", "overdue", "2026-09-04", "2026-08-25", None),
    _act("act-plat-sre-page", "mtg-2026-09-04-platform", "proj-platform", "person-maya", "Add SRE to the dual-write paging rotation.", "overdue", "2026-09-05", "2026-09-04", "seg-plat-20"),
    _act("act-mobile-contract-tests", "mtg-2026-09-03-mobile", "proj-mobile", "person-sam", "Keep identity contract tests running against staging even while blocked.", "open", "2026-09-12", "2026-09-03", "seg-mob-20"),
    _act("act-steer-graph-note", "mtg-2026-07-15-steering", "proj-platform", "person-jordan", "Write the dependency graph into the program RAID log.", "done", "2026-07-18", "2026-07-15", None),
    _act("act-plat-lag-repro", "mtg-2026-08-27-platform", "proj-platform", "person-priya", "Reproduce 4s p95 lag with production-sized payloads.", "overdue", "2026-09-05", "2026-08-27", None),
    _act("act-comp-access-logs", "mtg-2026-08-28-compliance", "proj-compliance", "person-chris", "Point compliance at the new access-log bucket once pipeline lands.", "open", "2026-10-01", "2026-08-28", None),
    _act("act-mobile-qa-matrix", "mtg-2026-07-22-mobile", "proj-mobile", "person-sam", "QA matrix for relaunch on iOS 18 and Android 15.", "done", "2026-08-05", "2026-07-22", None),
    _act("act-portal-a11y", "mtg-2026-08-11-portal", "proj-portal", "person-riley", "Accessibility pass on account settings.", "done", "2026-08-22", "2026-08-11", None),
    _act("act-pipe-debezium-docs", "mtg-2026-08-06-pipeline", "proj-pipeline", "person-chris", "Document Debezium connector config in the data wiki.", "done", "2026-08-12", "2026-08-06", None),
    _act("act-plat-capacity", "mtg-2026-09-04-platform", "proj-platform", "person-priya", "Confirm Redis and Postgres capacity for dual-write peak.", "open", "2026-09-13", "2026-09-04", "seg-plat-22"),
    _act("act-steer-follow-portal", "mtg-2026-09-02-steering", "proj-portal", "person-riley", "Brief Portal that they are two hops behind Platform, not directly blocked.", "done", "2026-09-03", "2026-09-02", "seg-steer-14"),
    _act("act-lead-budget-line", "mtg-2026-08-19-steering", "proj-platform", "person-dana", "Park Nimbus Auth budget as a contingency line, leadership-only.", "open", "2026-09-20", "2026-08-19", "seg-lead-16", "leadership"),
    _act("act-plat-rollback-script", "mtg-2026-09-04-platform", "proj-platform", "person-maya", "Check rollback script against last week's snapshot.", "overdue", "2026-09-06", "2026-09-04", "seg-plat-07"),
    _act("act-mobile-comms-oct15", "mtg-2026-08-12-mobile", "proj-mobile", "person-alex", "Correct marketing: launch stays October 15, delay is cancelled.", "done", "2026-08-13", "2026-08-12", None),
    _act("act-pipe-payments-hold", "mtg-2026-08-06-pipeline", "proj-pipeline", "person-chris", "Do not enable payments CDC until PII tags exist.", "done", "2026-08-20", "2026-08-06", None),
    _act("act-comp-vendor-skip", "mtg-2026-08-28-compliance", "proj-compliance", "person-jordan", "Close out extra vendor questionnaires as out of scope.", "done", "2026-09-02", "2026-08-28", None),
]

RISKS: list[dict[str, Any]] = [
    {"risk_id": "risk-dualwrite", "project_id": "proj-platform", "meeting_id": "mtg-2026-09-04-platform", "text": "Dual-write lag above 2s will desync mobile sessions at launch.", "severity": "high", "status": "open", "source_segment_id": "seg-plat-11", "visibility": "team"},
    {"risk_id": "risk-runbook", "project_id": "proj-platform", "meeting_id": "mtg-2026-09-04-platform", "text": "Cutover without a finished runbook has no tested rollback.", "severity": "high", "status": "open", "source_segment_id": "seg-plat-06", "visibility": "team"},
    {"risk_id": "risk-sla", "project_id": "proj-platform", "meeting_id": "mtg-2026-09-04-platform", "text": "Unsigned identity SLA means Mobile cannot promise uptime in store listing.", "severity": "high", "status": "open", "source_segment_id": "seg-plat-15", "visibility": "team"},
    {"risk_id": "risk-mobile-block", "project_id": "proj-mobile", "meeting_id": "mtg-2026-09-03-mobile", "text": "Mobile relaunch is date-locked to October 15 but blocked on platform identity.", "severity": "high", "status": "open", "source_segment_id": "seg-mob-08", "visibility": "team"},
    {"risk_id": "risk-portal-hop", "project_id": "proj-portal", "meeting_id": "mtg-2026-09-02-steering", "text": "Portal is transitively blocked by Platform even though its direct dependency is Mobile.", "severity": "med", "status": "open", "source_segment_id": "seg-steer-13", "visibility": "all"},
    {"risk_id": "risk-pii", "project_id": "proj-pipeline", "meeting_id": "mtg-2026-08-20-pipeline", "text": "Warehouse PII tags missing; compliance cannot start evidence.", "severity": "med", "status": "open", "source_segment_id": None, "visibility": "team"},
    {"risk_id": "risk-auth0-exit", "project_id": "proj-platform", "meeting_id": "mtg-2026-08-13-platform", "text": "Auth0 trial overrun if cancellation slips.", "severity": "low", "status": "mitigated", "source_segment_id": None, "visibility": "team"},
    {"risk_id": "risk-schema-freeze", "project_id": "proj-platform", "meeting_id": "mtg-2026-07-16-platform", "text": "Schema freeze blocking mobile contract tests.", "severity": "med", "status": "mitigated", "source_segment_id": None, "visibility": "team"},
    {"risk_id": "risk-nimbus", "project_id": "proj-platform", "meeting_id": "mtg-2026-08-19-steering", "text": "If in-house identity slips, Nimbus Auth acqui-hire is the only leadership fallback and is not visible to the team.", "severity": "high", "status": "open", "source_segment_id": "seg-lead-13", "visibility": "leadership"},
    {"risk_id": "risk-freeze-sre", "project_id": "proj-platform", "meeting_id": "mtg-2026-08-19-steering", "text": "Hiring freeze may leave identity without an SRE until November.", "severity": "high", "status": "open", "source_segment_id": "seg-lead-08", "visibility": "leadership"},
    {"risk_id": "risk-store-submit", "project_id": "proj-mobile", "meeting_id": "mtg-2026-09-03-mobile", "text": "Premature store submit would advertise a login that does not work.", "severity": "med", "status": "open", "source_segment_id": "seg-mob-16", "visibility": "team"},
    {"risk_id": "risk-lineage", "project_id": "proj-compliance", "meeting_id": "mtg-2026-08-28-compliance", "text": "SOC2 pack fails if pipeline lineage is late.", "severity": "med", "status": "open", "source_segment_id": None, "visibility": "team"},
]

AGENDAS: list[dict[str, Any]] = [
    {"agenda_id": "ag-mtg-2026-09-09-platform", "meeting_id": "mtg-2026-09-09-platform", "human_agenda": "Migration status, Q4 dates, hiring coverage.", "ai_agenda": None, "ai_agenda_sources": None, "generated_at": None, "generated_by": None, "status": "draft", "visibility": "team"},
    {"agenda_id": "ag-mtg-2026-09-10-mobile", "meeting_id": "mtg-2026-09-10-mobile", "human_agenda": "Launch date, platform blocker, store hold.", "ai_agenda": None, "ai_agenda_sources": None, "generated_at": None, "generated_by": None, "status": "draft", "visibility": "team"},
    {"agenda_id": "ag-mtg-2026-09-10-portal", "meeting_id": "mtg-2026-09-10-portal", "human_agenda": "Session SDK, billing mocks.", "ai_agenda": None, "ai_agenda_sources": None, "generated_at": None, "generated_by": None, "status": "draft", "visibility": "team"},
    {"agenda_id": "ag-mtg-2026-09-11-pipeline", "meeting_id": "mtg-2026-09-11-pipeline", "human_agenda": "PII tags, lineage catalog.", "ai_agenda": None, "ai_agenda_sources": None, "generated_at": None, "generated_by": None, "status": "draft", "visibility": "team"},
    {
        "agenda_id": "ag-mtg-2026-09-11-compliance",
        "meeting_id": "mtg-2026-09-11-compliance",
        "human_agenda": "Evidence inventory vs pipeline dates.",
        "ai_agenda": (
            "## Pre-generated example\n"
            "- Confirm SOC2 scope is lineage + access logs [decision:dec-soc2-scope]\n"
            "- PII classification still open [action:act-pipe-pii] [risk:risk-pii]\n"
        ),
        "ai_agenda_sources": '["dec-soc2-scope","act-pipe-pii","risk-pii","mtg-2026-08-28-compliance"]',
        "generated_at": "2026-09-05T18:00:00Z",
        "generated_by": "minutes-seed",
        "status": "draft",
        "visibility": "team",
    },
]
