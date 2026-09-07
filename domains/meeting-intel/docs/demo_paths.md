# Minutes — Harborline meeting intelligence

Four chat paths plus live CDC beats. Dates are relative to **2026-09-07**. Signed-in user is Maya Chen (`person-maya`, Platform eng lead, `access_role=team`).

Toggle `DEMO_USER_ROLE=leadership` (and `DEMO_USER_ID=person-dana`) to replay path 1 as an exec.

## Path 1 — Generate the Platform Migration agenda ⭐

Ask: **Generate the agenda for next week's Platform Migration sync.**

Expected:

1. `get_current_user_profile` then `get_current_time`.
2. Resolve `proj-platform` / upcoming `mtg-2026-09-09-platform`.
3. Active decisions only (not superseded Auth0 / schema-freeze).
4. Overdue actions first, grouped by owner:
   - `act-platform-runbook` Maya
   - `act-platform-dualwrite` Priya
   - `act-platform-sla` Jordan
   - plus `act-plat-lag-repro`, `act-plat-rollback-script`, `act-plat-sre-page`
5. Open risks `risk-dualwrite`, `risk-runbook`, `risk-sla`.
6. Reverse dependency: Mobile (`dep-mobile-platform`, blocking=true) depends on Platform.
7. Every bullet cites ids.
8. `save_ai_agenda` for `mtg-2026-09-09-platform`.

Follow-up: **Show me that agenda.** After RDI catches up, `filter_agenda_by_meeting_id` value=`mtg-2026-09-09-platform` returns the AI agenda next to the human three-liner ("Migration status, Q4 dates, hiring coverage.").

Team vs leadership: a team-role agenda must **not** include `dec-lead-freeze`, `dec-lead-nimbus`, `risk-nimbus`, or `act-lead-*`. Replay with `DEMO_USER_ROLE=leadership` to see the freeze / Nimbus Auth fallback.

## Path 2 — Overdue actions grouped by owner

Ask: **Which action items are overdue across all projects, grouped by owner?**

Expected: `filter_actionitem_by_status` value=`overdue`. Group by `owner_person_id`. Platform overdues belong to Maya, Priya, and Jordan and explain the Mobile block. Portal has `act-portal-wait-tag` (Riley). Do not list `status=open` items that are not overdue.

## Path 3 — Latest valid information (mobile launch)

Ask: **Did we decide to delay the mobile launch or not?**

Expected:

- `dec-mobile-delay-jul` (8 Jul, delay to November) is **superseded**.
- Current decision is `dec-mobile-keep-aug` (12 Aug): keep **October 15**.
- Cite `superseded_by_decision_id=dec-mobile-keep-aug`.
- Transcripts `mtg-2026-07-08-mobile` (summary) and `mtg-2026-09-03-mobile` (`seg-mob-02` / `seg-mob-03`) confirm the reversal.

Never present the July delay as current.

## Path 4 — Single-hop vs two-hop blocker

Ask: **What's blocking Customer Portal?**

Expected first hop: `filter_projectdependency_by_project_id` value=`proj-portal` → Mobile App Relaunch (`dep-portal-mobile`, blocking=false).

Follow-up: **And is that blocked?**

Second hop: `filter_projectdependency_by_project_id` value=`proj-mobile` → Platform Migration (`dep-mobile-platform`, blocking=true), then Platform overdue actions.

The agent should say the second question needed a second call. This is the honest single-hop vs graph point.

## Path 5 — Live CDC beats (not a chat path)

```bash
# Insert an overdue action in Postgres → Redis key action:act-cdc-live-overdue
psql "$MEETING_INTEL_PG" -f domains/meeting-intel/rdi/source-db/scripts/demo/add-overdue-action.sql
# Ask the agent again about overdue Platform items; the new row should appear.

# Mark it done → the answer should drop it
psql "$MEETING_INTEL_PG" -f domains/meeting-intel/rdi/source-db/scripts/demo/mark-action-done.sql

# Held-out extraction
psql "$MEETING_INTEL_PG" -f domains/meeting-intel/rdi/source-db/scripts/extra/transcript-05.sql
# In chat: extract follow-ups from meeting mtg-2026-09-01-pipeline-extra
```
