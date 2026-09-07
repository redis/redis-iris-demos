# Minutes workshop script (15–25 min)

Presenter notes for Harborline **Minutes**. Chat paths live in `[demo_paths.md](demo_paths.md)`. Dates are relative to **2026-09-07**. Signed-in user is Maya Chen (`person-maya`, `access_role=team`).

Do **not** `FLUSHDB` the iris-demos Redis Cloud target. Do **not** create another Cloud DB. RDI's backend is in-cluster Redis Enterprise `rdidb`. Leave GKE `meeting-intel-rdi` running unless the owner asks to destroy it.


| Clock       | Beat                         |
| ----------- | ---------------------------- |
| 0:00–3:00   | Architecture                 |
| 3:00–7:00   | Redis Insight                |
| 7:00–18:00  | UI paths 1–4                 |
| 18:00–22:00 | Live CDC                     |
| 22:00–25:00 | Optional YAML/code (or skip) |


---



## Beat 0 — Setup (before the room)

Laptop:

```bash
gcloud auth login
gcloud auth application-default login
gcloud container clusters get-credentials meeting-intel-rdi --zone us-central1-a --project central-beach-194106
make mi-pg-forward          # keep this terminal up (Postgres 5432)
DEMO_DOMAIN=meeting-intel make setup-surface
DEMO_DOMAIN=meeting-intel uv run python -m scripts.seed_memories
DEMO_DOMAIN=meeting-intel uv run python -m scripts.seed_langcache
# optional, for Simple RAG contrast:
make mi-embed-sidecar
make mi-demo-reset          # undo the last run's demo writes (see below)
make mi-verify
DEMO_DOMAIN=meeting-intel make dev
```

**Resetting between runs.** `make mi-demo-reset` diffs Postgres against the generated seed and issues row-level `DELETE`/`UPDATE` statements, so RDI carries every change into Redis on the normal CDC path. It removes what a run leaves behind — `act-cdc-live-overdue`, `act-live-*` from `create_action_item`, the `*-x-*` rows from `extract_from_transcript` — and clears AI agendas written by `save_ai_agenda` while keeping the human three-liner. It is idempotent and takes about 10s. Preview with `make mi-demo-reset-check` (runs in a transaction and rolls back, so RDI sees nothing).

Use `make mi-reset` only when you want a full re-snapshot. It re-seeds with `TRUNCATE`, and Debezium does **not** emit row deletes for `TRUNCATE`, so demo keys survive in Redis. Neither target needs `FLUSHDB`.

UI:   `` (backend `8040`). Confirm landing **Minutes** / Harborline, hero **What should we cover in the next meeting?**, mode toggle **Real-time Context** vs **Simple RAG**.

Redis Insight: same Cloud DB as `.env` `REDIS_*`. RDI API (if you show pipeline): ingress `http://34.172.4.76` (re-check `kubectl -n rdi get ingress`). Login is `POST /api/v1/login` with `RDI_PASSWORD` from secret `rdi-sys-config` (`RDI_REDIS_PASSWORD`), **not** Helm `api.jwtKey`.

---



## Beat 1 — Architecture (3 min)

Say this, then stop talking:

> Postgres is the system of record. There are **two Redis databases**. The Cloud DB is the **target**: JSON documents plus Context Surface indexes, LangCache, and Agent Memory. Inside GKE, Redis Enterprise `rdidb` is RDI's **backend** only (streams + processor state). Minutes **reads** Redis through Context Retriever. Minutes **writes** Postgres. RDI copies the row into Redis JSON within a few seconds.

Whiteboard (or slide) in one line:

```
Maya (chat) → LangCache / Memory → agent → Context Retriever (Redis JSON)
                                              ↑ RDI CDC
Maya write tools → Postgres (SoR) ────────────┘
```

What **not** to say: this is not JSONL `import_data`. Other packs in this repo load files; Minutes refuses that path (`manifest.data_plane = "rdi"`).

---



## Beat 2 — Redis Insight (4 min)

Browser: Redis Insight → the iris-demos Cloud DB. Browser search by prefix, then **JSON** view (not Hash).


| Click this key                    | Say this                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| `project:proj-platform`           | Platform Migration. `status=at_risk`. This is a document, not a chunk.                            |
| `meeting:mtg-2026-09-09-platform` | Next week's Platform weekly, `status=upcoming`. Path 1 writes the AI agenda for **this** meeting. |
| `action:act-platform-runbook`     | Maya's overdue cutover runbook. Context Retriever filters `status=overdue`.                       |
| `decision:dec-mobile-delay-jul`   | July delay to November. `status=superseded`, `superseded_by_decision_id=dec-mobile-keep-aug`.     |
| `decision:dec-mobile-keep-aug`    | Current truth: keep **October 15**. Path 3 must not treat July as current.                        |
| `action:act-cdc-live-overdue`     | May be missing until Beat 5. After SQL insert it appears here without a flush.                    |


Leave Insight open on `action:*` so the CDC key pop is visible later.

### Optional — wire Insight to RDI itself (2 min)

Redis Insight 2.54+ manages RDI from the **Redis Data Integration** tab, so you can show the pipeline definition and CDC status without a terminal. Add this endpoint **before** the room arrives; Insight downloads the deployed pipeline on first connect.

| Field    | Value                                                                                 |
| -------- | ------------------------------------------------------------------------------------- |
| Alias    | `meeting-intel-rdi`                                                                   |
| URL      | `https://34.172.4.76` — **https**, and re-check `kubectl -n rdi get ingress`           |
| Username | `default`                                                                             |
| Password | `kubectl -n rdi get secret rdi-sys-config -o jsonpath='{.data.RDI_REDIS_PASSWORD}' \| base64 -d` |

The ingress uses a self-signed cert, so accept the TLS warning. The password is the RDI **backend Redis** password, not Helm `api.jwtKey`. Same credential as `POST /api/v1/login`.

Two things worth showing:

- **Pipeline Management** — the deployed `config.yaml` (Postgres source host, tables) next to the per-table job YAMLs. This is the "no code, just config" claim, in the room, from the live server.
- **Pipeline Status** — engine state plus per-stream counters and processing performance. Leave this open in a second tab during Beat 4: the insert shows up as a counter tick on the `action_items` stream, which is the CDC story told in numbers rather than by refreshing a key.

If you skip this, Beat 4 still works. The Insight key pop is the more visceral demo; the status window is for the architect who asks "how do I operate this?"

---



## Beat 3 — UI paths 1–4 (11 min)

Mode: **Real-time Context**. Open the activity / tool-trace panel. Signed-in Maya (`person-maya`, team).

### Path 1 — Agenda (4 min) ⭐

Prompt (or starter card):

> Generate the agenda for next week's Platform Migration sync.

Audience should see:

1. Tools: `get_current_user_profile`, `get_current_time`, then `filter_meeting` / `filter_decision` / `filter_actionitem` / `filter_risk` / `filter_projectdependency` with **tag_conditions** (not the old `filter_*_by_`* names).
2. Overdue first, grouped by owner: Maya `act-platform-runbook`, Priya `act-platform-dualwrite`, Jordan `act-platform-sla`, plus `act-plat-lag-repro`, `act-plat-rollback-script`, `act-plat-sre-page`.
3. Active decisions only (not superseded Auth0 / schema-freeze).
4. Reverse hop: Mobile is blocked on Platform (`dep-mobile-platform`, `blocking=true`).
5. Ids on every bullet. **No** `dec-lead-freeze`, `dec-lead-nimbus`, `risk-nimbus`, `act-lead-`*.

If the model drafts but does not persist, second prompt:

> Save that agenda with save_ai_agenda for mtg-2026-09-09-platform.

Trace should show `save_ai_agenda`. Tool result note: wrote **Postgres**; RDI will copy. That is not `JSON.SET` on `agenda:`*.

Follow-up (wait ~3s):

> Show me that agenda.

Expected tool: `filter_agenda` with `tag_conditions` `meeting_id=mtg-2026-09-09-platform`. Human three-liner stays **"Migration status, Q4 dates, hiring coverage."** AI markdown sits next to it.

Optional (timeboxed): restart backend with `DEMO_USER_ROLE=leadership` `DEMO_USER_ID=person-dana` and replay Path 1 to show freeze / Nimbus Auth.

### Path 2 — Overdue by owner (2 min)

> Which action items are overdue across all projects, grouped by owner?

Expected: `filter_actionitem` `tag_conditions=[{field:status, value:overdue}]`. Maya / Priya / Jordan on Platform; Riley `act-portal-wait-tag` on Portal. Not `status=open`.

If LangCache answers immediately with only the three Platform items, say **"that's Fast"** (seeded FAQ). Follow with:

> Include Portal and every overdue, not just Platform.



### Path 3 — Latest valid decision (2 min)

> x

Expected: July `dec-mobile-delay-jul` is superseded; current is `dec-mobile-keep-aug` (October 15). Point back at Insight.

**Simple RAG contrast (30s):** toggle **Simple RAG**, same prompt. Vector search over transcript text can get the reversal right but cites chunk ids (`transcript_id: 3`) instead of navigable `decision:`* keys. Toggle back to Real-time Context.

### Path 4 — Single hop vs two hops (3 min)

> What's blocking Customer Portal?

First hop: `filter_projectdependency` `project_id=proj-portal` → Mobile (`dep-portal-mobile`, `blocking=false`).

If the model walks both hops in one turn, say so — then still ask:

> And is that blocked?

Second hop: `project_id=proj-mobile` → Platform (`dep-mobile-platform`, `blocking=true`). The point is **one hop per call**, not a graph database.

---



## Beat 4 — Live CDC (4 min)

Same session. Insight still filtered on `action:`. Port-forward still up.

**Check first:** `action:act-cdc-live-overdue` must **not** exist yet. If a previous run left it there, the reveal is spoiled — run `make mi-demo-reset` (see Beat 0) and refresh Insight.

```bash
psql "host=127.0.0.1 user=postgres dbname=postgres" \
  -f domains/meeting-intel/rdi/source-db/scripts/demo/add-overdue-action.sql
```

The script is an upsert, so re-running it on an existing row still bumps `updated_at` and still produces a CDC event. If neither the key nor `updated_at` changes in Insight within ~5s, RDI is down rather than slow: check `kubectl -n rdi get pods` and see the appendix.

Click `action:act-cdc-live-overdue` in Insight (JSON, `status=overdue`). Then in chat:

> Which Platform overdue actions should Maya see right now, including anything that just landed via CDC?

Audience should hear `act-cdc-live-overdue`. Optional close:

```bash
psql "host=127.0.0.1 user=postgres dbname=postgres" \
  -f domains/meeting-intel/rdi/source-db/scripts/demo/mark-action-done.sql
```

Ask overdue again; that id drops. Snapshot replay (if someone asks "how did the DB get full?") is `make mi-reset`, **never** `FLUSHDB`.

This session's `make mi-verify` CDC probe was **3479 ms** (earlier GKE bring-up recorded 4475 ms).

---



## Beat 5 — Optional YAML/code (3 min)

Only if an architect is in the room. Cite, don't paste walls of config.

**RDI job (JSON + key expression)** — `domains/meeting-intel/rdi/jobs/projects.yaml` lines 16–23:

```16:23:domains/meeting-intel/rdi/jobs/projects.yaml
output:
  - uses: redis.write
    with:
      connection: target
      data_type: json
      on_update: merge
      key:
        expression: concat(['project:', project_id])
        language: jmespath
```

Same pattern on `rdi/jobs/action_items.yaml` (`action:` + `action_id`) and `rdi/jobs/decisions.yaml` (`decision:` + `decision_id`).

**Pipeline source host (from GKE)** — `domains/meeting-intel/rdi/pipeline-config.yaml` lines 6–8, filled by `deploy_pipeline.py` line 37 (`postgres.meeting-intel.svc.cluster.local`):

```6:8:domains/meeting-intel/rdi/pipeline-config.yaml
    connection:
      type: postgresql
      host: ${SOURCE_DB_HOST}
```

```37:37:domains/meeting-intel/rdi/deploy_pipeline.py
        "${SOURCE_DB_HOST}": _env("MEETING_INTEL_RDI_SOURCE_HOST") or "postgres.meeting-intel.svc.cluster.local",
```

**Writes are Postgres only** — `domains/meeting-intel/tools.py` line 1 and `postgres.py` lines 39–41:

```1:1:domains/meeting-intel/tools.py
"""Postgres write tools. RDI owns Redis keys; these never JSON.SET synced documents."""
```

```39:41:domains/meeting-intel/postgres.py
RDI_NOTE = (
    "Wrote to Postgres (system of record). RDI will copy this into Redis within seconds. "
```

**FLUSHDB refused** — `Makefile` lines 167–171:

```167:171:Makefile
flush-redis:
	@if [ "$(DOMAIN)" = "meeting-intel" ]; then \
		echo "Refusing to FLUSHDB for meeting-intel: that would wipe RDI-owned keys."; \
		echo "Use 'make mi-reset' (re-seed Postgres + RDI snapshot) instead."; \
		exit 1; \
```

**Visibility ACL (field tag, not key pattern)** — `generated_models.py` lines 147–149 and prompt lines 55–58:

```147:149:domains/meeting-intel/generated_models.py
    visibility: str = ContextField(
        description="ACL: team, leadership, all",
        index="tag",
```

```55:58:domains/meeting-intel/prompt.py
1. ALWAYS CALL get_current_user_profile first. Honor access_role:
   - access_role=team → NEVER return or cite records whose visibility is "leadership".
     Filter meetings, decisions, actions, risks, and agendas with visibility team or all.
   - access_role=leadership → may read every visibility.
```

Context Retriever 2.0 filter tools take `tag_conditions` (`field` + `value`). Nested Pydantic args are JSON-encoded in `backend/app/langgraph_agent.py` `_jsonable` (lines 41–56) before the MCP call. Single-parameter tools such as `get_project_by_id` declare only `id`; `_with_single_arg_alias` (lines 358–385) renames a lone mismatched argument (`project_id`) so the trace stays green.

---



## Appendix — If something is down


| Symptom                                 | What to do                                                                                                                                      |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `gcloud` reauth failed                  | `gcloud auth login` and `gcloud auth application-default login`. Do not fake kubectl.                                                           |
| Cluster / IAM / API gone                | Stop. Do not recreate unless asked.                                                                                                             |
| Postgres CrashLoop `lost+found`         | `PGDATA=/var/lib/postgresql/data/pgdata` in `rdi/terraform/k8s/postgres.yaml`.                                                                  |
| `make mi-pg-forward` fails              | Need kubeconfig (`gcloud container clusters get-credentials …`).                                                                                |
| Write tools "Postgres write failed"     | Port-forward died. Restart `make mi-pg-forward`.                                                                                                |
| Redis does not change after demo SQL    | RDI is down, not slow. `kubectl -n rdi get pods`; if `processor`/`collector-source` are `CrashLoopBackOff`, run `make mi-rdi-fix-port` (~90s), then re-run the SQL. |
| `mi-verify` CDC timeout                 | Processor/collector crash-loop. Check `rdidb` **port**: Helm `connection.port` vs `secret/redb-rdidb`. `make mi-rdi-fix-port` does this. See `rdi/README.md`. |
| Demo keys already in Redis before Beat 4 | Previous run's leftovers. `make mi-demo-reset` (row-level CDC deletes), then refresh Insight.                                                   |
| RDI API 401                             | Password from `rdi-sys-config` / `RDI_REDIS_PASSWORD`, not `jwtKey`. Ingress IP may have changed.                                               |
| Context surface 404                     | `uv run python scripts/setup_surface.py --domain meeting-intel --force-create` (reuses the same Cloud DB).                                      |
| `make flush-redis DOMAIN=meeting-intel` | Expected refusal. Snapshot = `make mi-reset`. Deltas = SQL under `rdi/source-db/scripts/demo/`.                                                 |
| Landing is another domain               | `.env` `DEMO_DOMAIN=meeting-intel`, then restart `make dev`.                                                                                    |
| Guardrail blocks "Show me that agenda." | Domain pack includes that phrase as in-scope; restart backend after pulling.                                                                    |
| Filter tools JSON-serialize errors      | Need the `_jsonable` MCP wrapper on this branch.                                                                                                |
| `get_project_by_id` "Tool input validation failed" (`id` Field required) | Model sent `project_id`. Needs the `_with_single_arg_alias` wrapper and the `id=` prompt hint on this branch; the agent recovers either way, but the trace shows red. |


**Snapshot vs CDC:** first pipeline deploy used `snapshot.mode: initial`. Replay bulk load with `make mi-reset` (re-seed Postgres + RDI `/pipelines/reset`). Live demo uses SQL deltas. Neither needs an empty Redis.