# Spec: `meeting-intel` — a reusable meeting-intelligence demo domain (RDI + Redis Iris)

**Audience:** a coding agent extending `redis/redis-iris-demos`.
This pack is a **fictional** Harborline / Minutes dataset. It is not a customer
engagement dump and does not describe any real company.

---

## 1. Why this exists

The demo needs a meetings-and-projects corpus so three Iris stories share one dataset:

> Create the agenda for the next meeting based on previous meeting information. Retrieve
> previous decisions, actions, and risks. Identify incomplete and overdue actions. Identify
> dependencies between projects. Trace generated content back to the relevant meeting
> information and memory.

Useful retrieval checks on that corpus: setup/dev time · semantic relevance · filtering by
date/project/access permissions/metadata · relationship and dependency identification ·
response quality.

Today the RDI demos ship with the Chinook music dataset (Artist/Album/Track). That proves CDC
works but says nothing about the use case above. This spec replaces it with a **meetings /
projects** dataset that is reused across three things at once:

1. **RDI fundamentals** — change a row in Postgres, watch it land in Redis in real time.
2. **Agent Memory / "latest valid information"** — update a row, show supersession.
3. **Retrieval comparison + agenda generation** — the same rows become the corpus that
   Context Retriever, vector search, and hybrid search are compared over.

Postgres is the system of record. RDI syncs it into Redis. A `redis-iris-demos` domain pack
puts a Context Surface, Agent Memory, LangCache, and Semantic Routing on top.

## 2. Non-goals

- No Neo4j / graph database integration. Single-hop relationships via Context Retriever
  only; the seed data deliberately includes a multi-hop dependency chain so the *limit* can
  be shown honestly, not papered over.
- No production hardening. Local Docker Compose is the target.
- No new UI beyond what the `redis-iris-demos` frontend already provides per domain.
- No Chinook compatibility. Remove it from this pipeline; don't try to keep both.

## 3. Architecture

```
 Postgres (system of record)         RDI (CDC + transform)        Redis
 ┌────────────────────────┐    ┌──────────────────────────┐   ┌────────────────────────┐
 │ projects               │    │ Debezium collector       │   │ JSON docs, one per row │
 │ people                 │──▶ │ job YAML per table:      │──▶│ key = <prefix>:<id>    │
 │ meetings               │    │  row → JSON, key prefix, │   │ search indexes         │
 │ meeting_participants   │    │  type coercion, dates    │   │ (Context Surface owns) │
 │ transcripts            │    └──────────────────────────┘   └───────────┬────────────┘
 │ decisions              │                                               │
 │ action_items           │                                               ▼
 │ risks                  │                                  Context Surface (read tools)
 │ project_dependencies   │                                  Agent Memory · LangCache
 │ agendas                │◀──── write tool (agenda, action    Semantic Routing
 └────────────────────────┘      items, extraction) ─ agent ◀── LangGraph ReAct agent
```

**Rule #1 — one writer per key.** RDI owns every key it syncs. The agent never writes those
keys directly. All writes (AI agenda, new action items, extracted decisions) go to
**Postgres** through a dedicated write tool; RDI propagates them to Redis within seconds.
This is a feature, not a workaround: the write-back *is* the CDC demo.

**Rule #2 — Context Retriever is read-only.** Treat it as such. Confirm in
`backend/app/context_surface_service.py` that only read tools are exposed; if a write path
exists, still do not use it for RDI-owned keys.

## 4. Data model

Postgres schema (`sql/schema.sql`). All PKs are short, human-readable strings (e.g.
`proj-platform`, `mtg-2026-08-27-platform`) so keys are legible in Redis during a live demo.

| Table | Purpose | Notable fields |
|---|---|---|
| `projects` | The 5 workstreams | `project_id, name, status, team, lead_person_id, target_date` |
| `people` | ~8 participants | `person_id, name, role, team` |
| `meetings` | Past + one upcoming per project | `meeting_id, project_id, title, meeting_date, kind (sync\|steering\|retro), status (held\|upcoming), summary, visibility (team\|leadership\|all)` |
| `meeting_participants` | Who attended | `meeting_id, person_id` |
| `transcripts` | Raw speaker-labelled text for a subset of meetings | `transcript_id, meeting_id, segment_id, start_ts, speaker_person_id, text` (one row per segment) |
| `decisions` | Derived | `decision_id, meeting_id, project_id, text, decided_at, status (active\|superseded), superseded_by_decision_id, source_segment_id` |
| `action_items` | Derived | `action_id, meeting_id, project_id, owner_person_id, text, status (open\|done\|overdue), due_date, created_at, updated_at, source_segment_id` |
| `risks` | Derived | `risk_id, project_id, meeting_id, text, severity (low\|med\|high), status (open\|mitigated), source_segment_id` |
| `project_dependencies` | Cross-project edges | `dependency_id, project_id, depends_on_project_id, description, blocking (bool)` |
| `agendas` | Human + AI agenda for an upcoming meeting | `agenda_id, meeting_id, human_agenda (short text), ai_agenda (text/markdown), ai_agenda_sources (JSONB: meeting/decision/action/risk ids used), generated_at, generated_by, status (draft\|approved)` |

**Provenance is mandatory.** Every derived row (`decisions`, `action_items`, `risks`) must
carry `meeting_id` and, when it came from a transcript, `source_segment_id`. `agendas.ai_agenda_sources`
must list every id the agent relied on. This is what makes "trace generated content back to
the relevant meeting information" a live demo instead of a claim.

**Access filtering is real.** `visibility` on meetings (and inherited by their decisions/
actions/risks) is the field the Context Surface ACL filters on. Seed at least one
`leadership`-only steering meeting whose decisions should *not* surface for a `team`-role user.

## 5. Seed data — the storyline

Fictional mid-size software company, ~10 weeks of history ending the week before the demo,
plus one **upcoming** meeting per project with no AI agenda yet. Keep it realistic and
internally consistent — dates, owners, and statuses must agree across tables.

**Projects (5) and dependency graph — includes a deliberate 2-hop chain:**

```
Customer Portal ──depends on──▶ Mobile App Relaunch ──depends on──▶ Platform Migration
Compliance Audit ──depends on──▶ Data Pipeline Modernization
```
One edge (`Mobile App → Platform Migration`) is `blocking = true`. The 2-hop chain
(`Customer Portal → Mobile App → Platform Migration`) is intentional: a single-hop tool
answers "what does Customer Portal depend on?" but *not* "is Customer Portal transitively
blocked by Platform Migration?" without chaining two calls. Keep it in the data.

**Volumes (minimums):**

| Entity | Count | Notes |
|---|---|---|
| people | 8 | Mixed roles: PM, eng lead, engineers, one exec |
| meetings | 16–20 held + 5 upcoming | Weekly syncs per project + 2–3 cross-project steering meetings |
| transcripts | 4 meetings fully transcribed | The most recent held meeting for Platform Migration, Mobile App, and two steering meetings. 800–1,500 words each, speaker-labelled, 20–40 segments with timestamps. Other meetings have `summary` only |
| decisions | 20–25 | ≥3 **superseded** pairs (decision in week 3 reversed in week 7, linked via `superseded_by_decision_id`) — this is the "latest valid information" demo |
| action_items | 35–45 | Mix: ~50% done, ~30% open, ~20% overdue (due_date < today, status open). Several overdue ones must belong to Platform Migration since that's the demo target |
| risks | 10–12 | Several high-severity, some mitigated, at least one that appears in a steering transcript |
| agendas | 5 | One per upcoming meeting; `human_agenda` populated (1–3 short lines), `ai_agenda` **NULL** for all but one pre-generated example |

**Content coherence requirements:**
- The transcripts must actually contain the decisions/actions/risks attributed to them, at
  the `source_segment_id` cited. A reviewer should be able to open the segment and see it.
- The superseded-decision pairs must both be visible in transcripts or summaries so the
  "which is current?" question has a checkable answer.
- Overdue Platform Migration items must plausibly explain why Mobile App is blocked — that's
  the narrative the AI agenda should surface.
- Dates: use real calendar dates relative to today (2026-09-07). Upcoming meetings fall in
  the week of Sept 8–12.

Author the seed as `sql/seed.sql` (idempotent — drop/recreate or `ON CONFLICT DO NOTHING`)
so the demo can be reset in one command. If the domain-pack skill wants a Python
`data_generator.py`, generate the SQL from it rather than maintaining two copies.

## 6. Transcript → derived data (extraction)

Two modes; ship both, prioritize the first:

1. **Prepopulated (default, demo-safe):** decisions/actions/risks for the 4 transcribed
   meetings are hand-authored into `seed.sql` with correct `source_segment_id`s.
2. **Live extraction tool (`extract_from_transcript(meeting_id)`):** reads the transcript
   segments, prompts an LLM to return structured JSON (decisions, action items with owners
   and due dates, risks with severity) each tagged with the `segment_id` it came from, then
   **writes to Postgres**. Include a 5th transcript in `sql/extra/` that is *not* in the
   default seed, so this can be run live: load transcript → run extraction → watch derived
   rows appear in Redis via RDI → they're immediately visible to Context Retriever.

Extraction output must be validated (owner must exist in `people`, meeting_id must exist,
dates parse) before insert. Reject and log otherwise — never write partial garbage.

## 7. The agenda entity and AI agenda generation

`agendas.human_agenda` is the short, human-typed list ("Migration status, Q4 dates, hiring").
`agendas.ai_agenda` is generated by the agent for an upcoming meeting by:

1. Resolving the meeting → project → related meetings (same project + steering meetings that
   referenced it) via Context Retriever.
2. Pulling **active** decisions (not superseded), **open/overdue** action items, **open**
   risks, and the project's dependencies (and what depends on it).
3. Respecting the requesting user's `visibility` — a team-role user's agenda must not leak
   leadership-only decisions.
4. Producing a structured agenda: proposed topics, carried-over overdue items with owners,
   decisions to confirm/revisit, risks to review, dependency status — **each bullet with the
   ids it came from**.
5. Persisting via write tool `save_ai_agenda(meeting_id, ai_agenda, sources)` → Postgres →
   RDI → Redis. The saved agenda is then retrievable through Context Retriever in the same
   session, which closes the loop on stage.

The human agenda and AI agenda are stored side by side deliberately — the demo moment is
"here's the three lines the PM wrote; here's what the agent found that they'd have missed,
and here's exactly where each item came from."

## 8. Agent tools

**Read (via Context Surface / Context Retriever — auto-generated from `schema.py`):**
entities + single-hop relationships: project→meetings, meeting→decisions/actions/risks/
participants/transcript segments, project→dependencies (both directions), person→action items.

**Write (custom tools in the domain pack, hitting Postgres directly):**
- `save_ai_agenda(meeting_id, ai_agenda, sources)`
- `create_action_item(meeting_id, project_id, owner_person_id, text, due_date)`
- `update_action_item_status(action_id, status)`
- `extract_from_transcript(meeting_id)` (Section 6)

Every write tool returns the id written and a note that the change will appear via RDI; the
agent should re-read through Context Retriever to confirm rather than assume.

**Memory:** seed 2–3 long-term memories for the demo user (e.g. "prefers agendas grouped by
owner", "is the lead for Platform Migration"). Session memory carries the working context of
the conversation. Where possible show memory being used to *shape* the agenda, not just
recall facts.

## 9. RDI: the demo repos, what to take from each, and how to integrate

### 9.1 Reality check on how RDI runs

RDI is **not** shipped as a single Docker image you can drop into a Compose file. The realistic
local options are: (a) RDI on a local Kubernetes cluster via Helm, or (b) RDI on a VM install,
or (c) RDI Cloud (managed, needs PrivateLink to the source — not laptop-friendly). This spec
uses **(a)**. Plan for it: a local k8s (Docker Desktop k8s, `kind`, or `minikube`) with at
least **4 CPUs / 8 GB RAM / 25 GB disk** dedicated to the cluster, or RDI pods will crash-loop.

RDI also needs **two** Redis databases: its own backend DB (streams + processor state) and the
**target** DB where synced data lands. Keep them separate. The target DB for this project is
**the same Redis Cloud database `redis-iris-demos` already uses** — that is what the Context
Surface indexes. Don't introduce a third Redis.

### 9.2 The three repos and what to take from each

| Repo | What it actually is | Take from it |
|---|---|---|
| **`redis-developer/postgres-to-redis-rdi-demo`** (Ricardo Ferreira) — **primary base** | The most complete, documented Postgres→Redis RDI demo. *Not Chinook* — an e-commerce schema (`Category`, `Product`, `Customer`, `Employee`, `Supplier`, `"order"`, `OrderItem`, `ProductSupplier`, `"user"`). `source-db/` = Docker Compose with a Debezium-ready Postgres + pgAdmin, seeded from `source-db/scripts/initial-load.sql`. `rdi-deploy/` = scripted Helm deployment of RDI onto local k8s (`rdi-deploy-localdb.sh` also stands up a local Redis Enterprise for RDI's backend DB; `rdi-deploy-clouddb.sh` uses Redis Cloud for it). `target-db/` = Terraform for a free-tier Redis Cloud target. `pipeline-config.yaml` = the RDI pipeline (source/target connection). `custom-job-v2.yaml` = a job that converts Hash→JSON and adds derived fields. `demo-add-user.sql` / `demo-modify-user.sql` / `demo-multiple-users.sql` = live CDC beats. `generate_random_users()` in the seed = a plpgsql continuous change generator. | **Everything structural.** The `source-db/` Compose pattern, the `rdi-deploy/` scripts, the pipeline + job YAML as syntax references, the demo-SQL-beat pattern, and the continuous-generator idea. Replace the e-commerce schema/seed with ours. Skip `target-db/` Terraform — our target already exists. |
| **`Redislabs-Solution-Architects/rdi-quickstart-postgres`** (private) | The Postgres container referenced by the official RDI quickstart docs. Chinook dataset, `wal_level=logical`, Debezium user (`dbzuser` / `dbz`) and publication pre-configured. | Only its **Postgres CDC prerequisites** (logical decoding config, replication user/grants, publication setup) if the primary repo's Postgres image doesn't already cover them. Do not use its data. |
| **`redis-developer/speedup-slowapp-with-redis-di`** (Ricardo Ferreira) | Earlier sibling of the primary repo: RDI on local k8s + Terraform, moving/transforming on-prem Postgres into Redis Cloud. | Reference only, for k8s/Terraform variations if the primary repo's scripts hit a snag. Don't build on it. |

Official references to keep open: RDI docs
(https://redis.io/docs/latest/integrate/redis-data-integration/), the quickstart
(…/quick-start-guide/), "Prepare PostgreSQL" (…/data-pipelines/prepare-dbs/postgresql/), and
transformation examples (…/data-pipelines/transform-examples/).

### 9.3 How the RDI pieces integrate into `redis-iris-demos`

Everything RDI-related lives **inside the domain**, so other domains are untouched and the
whole thing is portable:

```
domains/meeting-intel/
  rdi/
    source-db/
      docker-compose.yml          # from primary repo; Postgres (Debezium-ready) + pgAdmin
      scripts/
        00-schema.sql             # Section 4
        01-seed.sql               # Section 5 (idempotent)
        extra/transcript-05.sql   # held-out transcript for live extraction (Section 6)
        demo/                     # live CDC beats (Section 11)
          add-overdue-action.sql
          mark-action-done.sql
          add-dependency.sql
    deploy/                       # vendored from primary repo's rdi-deploy/, minimally adapted
      rdi-deploy-localdb.sh
      rdi-undeploy-localdb.sh
    pipeline-config.yaml          # source = local Postgres, target = redis-iris-demos Redis Cloud DB
    jobs/
      projects.yaml               # one job per table → JSON, explicit key, type coercion
      meetings.yaml
      ...
      agendas.yaml
    README.md                     # prefix map, ports, reset procedure, known failure modes
```

**Makefile additions** (domain-scoped; wire into `make setup DOMAIN=meeting-intel`):

| Target | Does |
|---|---|
| `make mi-pg-up` | `docker compose up -d` in `rdi/source-db` → Postgres seeded from `00-schema.sql` + `01-seed.sql` |
| `make mi-rdi-deploy` | Runs `deploy/rdi-deploy-localdb.sh` (RDI + its backend Redis on local k8s) |
| `make mi-rdi-pipeline` | Deploys `pipeline-config.yaml` + `jobs/*.yaml` to RDI **non-interactively** (see 9.4), waits for snapshot to finish |
| `make mi-verify` | Asserts Redis key counts == Postgres row counts per table; prints CDC latency for one insert |
| `make mi-reset` | Re-applies seed to Postgres, **resets the RDI pipeline so it re-snapshots**, re-verifies |
| `make mi-pg-down` / `make mi-rdi-undeploy` | Teardown |

`make setup DOMAIN=meeting-intel` order: `mi-pg-up` → `mi-rdi-deploy` (skip if already
deployed) → `mi-rdi-pipeline` → `mi-verify` → generate Context Surface models → create Context
Surface + indexes → seed memory → seed LangCache. **Skip the generic "generate JSONL / load
data" steps and the generic Redis flush for this domain** — see the gotchas below.

### 9.4 Integration gotchas (each one has bitten someone)

1. **`make setup` flushes Redis.** For every other domain that's fine; for this one it wipes
   RDI's synced keys and RDI will *not* re-send them on its own. Either exclude the flush for
   `meeting-intel`, or immediately follow it with an RDI pipeline **reset** so a fresh snapshot
   runs. `make mi-reset` must always do the latter.
2. **Index creation vs. snapshot timing.** Create the Context Surface indexes *after* RDI's
   initial snapshot completes and `mi-verify` passes, or you'll index an empty/partial dataset.
   Poll RDI pipeline status (or key counts) rather than sleeping.
3. **k8s → host networking.** RDI runs inside the cluster; Postgres runs in Docker on the host.
   `localhost` in `pipeline-config.yaml` will not resolve. Use `host.docker.internal` (kind /
   Docker Desktop) or `host.minikube.internal` (minikube). On minikube you also need
   `minikube tunnel` running for Redis Insight / the RDI API to be reachable.
4. **Deploy the pipeline without clicking.** The primary repo's README walks through Redis
   Insight's RDI UI. That's fine for a one-off, but `make mi-rdi-pipeline` must be scriptable:
   prefer the RDI API / `redis-di deploy` / Helm pipeline values (the deploy scripts already
   install a `pipeline` Helm chart) over UI steps. Keep Redis Insight as the *monitoring* view
   during the live demo — it's a good visual for CDC landing.
5. **Key naming.** RDI's default key format is not what the Context Surface expects. Every
   job must set an explicit key expression so keys come out as `<prefix>:<id>` (e.g.
   `meeting:mtg-2026-08-27-platform`). Match `custom-job-v2.yaml`'s syntax; verify against the
   transform-examples docs rather than guessing.
6. **Output type.** Force `data_type: json` in every job. The Context Surface indexes JSON.
   Hashes (RDI's default) will silently not be indexed.
7. **Two Redis DBs, two passwords.** RDI backend DB creds come from `rdi-values.yaml` (written
   by the deploy script). Target DB creds are the `redis-iris-demos` `.env` values. Don't
   cross them; put both in the domain `README.md`.
8. **Postgres CDC prereqs.** `wal_level=logical`, a replication-capable user, and a publication
   covering all 10 tables. If you swap the Postgres image, re-check these — the primary repo's
   image already has them; the quickstart repo is the fallback reference.
9. **Snapshot state.** After the initial snapshot RDI moves to streaming. If the pipeline
   shows "snapshot" for a long time on this small dataset, something's wrong (usually
   networking or the publication). Surface pipeline state in `mi-verify` output.
10. **NULLs and JSONB.** `agendas.ai_agenda` is NULL until generated; `ai_agenda_sources` is
    JSONB. Confirm both round-trip correctly (NULL → absent/null field, JSONB → nested JSON,
    not a string).

### 9.5 Job-level requirements

- One job per table. Output **JSON**, explicit key expression, `on_update: merge`.
- Coerce types in the transform: dates → ISO-8601 strings, booleans → true/false, JSONB →
  nested JSON, numeric ids stay strings.
- Prefix map, decided once and recorded in the domain `README.md`: `project:`, `person:`,
  `meeting:`, `participant:`, `transcript:`, `decision:`, `action:`, `risk:`, `dependency:`,
  `agenda:`. `EntitySpec` prefixes in `schema.py` must match these exactly.
- Verify CDC end-to-end before wiring the agent: insert → key appears; update → field
  changes; delete → key removed. Record observed latency in the README.

### 9.6 Open design decision — embeddings RDI does not emit vectors. Investigate how existing
domains populate vector fields: does the loader embed, or does the Context Surface embed at
index time (Embedder backend)? Then:
- If the Context Surface embeds server-side: nothing extra needed, just declare the vector
  field on `transcripts.text`, `decisions.text`, `risks.text`, `meetings.summary`.
- If the loader embeds client-side: add a small **embedding sidecar** — RDI writes the JSON
  doc *and* an event to a Redis Stream; a consumer reads the stream, embeds the text field,
  and `JSON.SET`s the vector field *only* (a field RDI does not own, so Rule #1 holds).
Document which path was taken and why.

## 10. Domain pack (`redis-iris-demos`)

Use the repo's Codex skill: `.codex/skills/domain-pack-authoring/SKILL.md`, and scaffold with
`make create-domain DOMAIN=meeting-intel`. Implement the `DomainPack` protocol
(`backend/app/core/domain_contract.py`). Deliver every file the README lists for a domain:

- `domains/meeting-intel/schema.py` — `EntitySpec`s for the tables in Section 4, with
  relationships and the `visibility` ACL field.
- `domains/meeting-intel/domain.py` — branding (working name **"Minutes"**; placeholder logo
  is fine), guardrail routes (block off-topic; allow meeting/project/agenda/action queries),
  seed memories, seed cache entry.
- `domains/meeting-intel/prompt.py` — system prompt with tool hints for agenda generation,
  overdue-item triage, dependency lookup, provenance ("always cite ids").
- `domains/meeting-intel/data_generator.py` — emits `seed.sql` (see Section 5).
- `domains/meeting-intel/docs/demo_paths.md` — the four scripted paths in Section 11.
- Frontend background SVGs — simple, under the size limits in the README.

**Data-path change:** `make setup` currently generates JSONL and loads Redis directly. For
this domain, the "load data" step must instead (re)apply `schema.sql` + `seed.sql` to
Postgres and let RDI populate Redis. Add a `make setup DOMAIN=meeting-intel` path that does
this and waits/polls until the expected key counts are present before creating the Context
Surface indexes. Do not break the other domains.

## 11. Scripted demo paths (write these into `demo_paths.md`)

1. **"Generate the agenda for next week's Platform Migration sync."** Agent pulls history,
   overdue items, active decisions, risks, dependencies; produces agenda with ids; saves it.
   Then: "show me that agenda" → retrieved via Context Retriever (round-trip via RDI).
2. **"Which action items are overdue across all projects, grouped by owner?"** Metadata
   filtering on `status`, `due_date`, `owner`.
3. **"Did we decide to delay the mobile launch or not?"** Two conflicting decisions; the
   agent must return the *current* one and cite the superseding decision. (Latest-valid-info.)
4. **"What's blocking Customer Portal?"** Single hop → Mobile App. Follow-up: "and is *that*
   blocked?" → second hop → Platform Migration's overdue items. Narrate that the second
   question required a second call — this is the honest single-hop vs. graph point.
5. *(Live CDC beats, not a chat path)* Insert a new overdue action item in Postgres → visible
   in Redis and to the agent within seconds. Update it to `done` → agent's answer changes.
   Run `extract_from_transcript` on the 5th transcript → derived rows appear.

Also run path 1 as a `leadership` user vs. a `team` user and show the agenda differs.

## 12. Acceptance criteria

- [ ] `docker compose up` + one `make` target yields Postgres seeded, RDI streaming, Redis
      populated, Context Surface created, agent running at `localhost:3040`.
- [ ] Key counts in Redis match row counts in Postgres for all 10 tables.
- [ ] Insert/update/delete in Postgres reflected in Redis; latency recorded in README.
- [ ] All four chat demo paths produce correct, id-cited answers against the seed data.
- [ ] Superseded decision is never returned as current; superseding id is cited.
- [ ] A `team`-role user cannot see `leadership`-visibility decisions in any path.
- [ ] `save_ai_agenda` round-trips: written to Postgres, readable via Context Retriever.
- [ ] `extract_from_transcript` on the held-out transcript yields ≥3 decisions/actions/risks
      with valid `source_segment_id`s, and rejects malformed output.
- [ ] `make reset` returns to a clean seeded state in one command; re-running demo paths
      gives the same results.
- [ ] Other domains in `redis-iris-demos` still `make setup` and run.
- [ ] `README.md` documents: prefix map, embedding decision, reset procedure, known
      failure modes (slow container start, port conflicts, RDI snapshot vs. streaming state).

## 13. Phasing (do P0 first, confirm, then continue)

- **P0 — Data + pipeline.** In this order: (1) clone the primary RDI repo and get *its*
  demo working unmodified on local k8s first — this proves the cluster sizing, networking,
  and deploy scripts before anything is customized; (2) vendor `source-db/` + `rdi-deploy/`
  into `domains/meeting-intel/rdi/` per 9.3; (3) swap in `00-schema.sql` + `01-seed.sql`
  (incl. transcripts); (4) write one job per table; (5) point the target at the
  `redis-iris-demos` Redis Cloud DB; (6) `mi-verify` passes, CDC latency recorded. No agent
  yet. *This alone already upgrades the RDI fundamentals demo.*
- **P1 — Domain pack + read paths.** Context Surface over the data, guardrails, prompt,
  demo paths 2–4 working. Access filtering verified.
- **P2 — Write-back.** `save_ai_agenda`, `create_action_item`, `update_action_item_status`;
  demo path 1 end to end including the round-trip read.
- **P3 — Extraction.** `extract_from_transcript` + held-out transcript; live CDC beats.
- **P4 — Polish.** Branding, backgrounds, memory seeding that visibly shapes output.

Stop and report after each phase with: what works, what's flaky, observed latencies, and
anything that had to deviate from this spec (and why).

## 14. Things to investigate rather than assume

1. How existing domains declare and populate vector fields (drives the Section 9 decision).
2. Whether `EntitySpec` supports a per-entity ACL/visibility field natively or whether the
   filter has to be applied in the tool wrapper.
3. RDI's handling of JSONB → nested JSON and of NULLs (the `ai_agenda` NULL case matters).
4. Whether Context Surface index creation must happen *after* RDI's initial snapshot, or can
   precede it (affects `make setup` ordering) — assume *after* until proven otherwise.
5. Whether the primary repo's Postgres image already has `wal_level=logical`, the replication
   user, and a publication that will cover our 10 tables, or whether the publication is
   table-scoped and must be recreated after the schema swap.
6. The exact RDI job syntax for an explicit key expression + `data_type: json` (copy from
   `custom-job-v2.yaml`, confirm against the transform-examples docs).
7. How to deploy/reset the pipeline non-interactively (RDI API vs. `redis-di` CLI vs. Helm
   pipeline values) — this decides whether `make mi-rdi-pipeline` and `make mi-reset` are
   real one-command targets or need a manual Redis Insight step.
8. Whether the local-k8s RDI deploy scripts assume Redis Enterprise for the *target* as well
   as the backend, and what changes are needed to point the target at Redis Cloud instead.
