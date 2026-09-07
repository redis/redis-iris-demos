# meeting-intel RDI

Postgres is the system of record. RDI copies each row into Redis JSON. Minutes (the agent) reads Redis through Context Retriever and writes **only** through Postgres tools.

## Prefix map

| Postgres table | Redis key |
|---|---|
| `projects` | `project:{project_id}` |
| `people` | `person:{person_id}` |
| `meetings` | `meeting:{meeting_id}` |
| `meeting_participants` | `participant:{participant_id}` |
| `transcripts` | `transcript:{transcript_id}` |
| `decisions` | `decision:{decision_id}` |
| `action_items` | `action:{action_id}` |
| `risks` | `risk:{risk_id}` |
| `project_dependencies` | `dependency:{dependency_id}` |
| `agendas` | `agenda:{agenda_id}` |

`EntitySpec.redis_key_template` in `schema.py` matches this map. Jobs in `jobs/` set `data_type: json` and an explicit key expression.

## Two Redis databases

| Role | Where | Credentials |
|---|---|---|
| **Target** (synced JSON + Context Surface indexes) | The redis-iris-demos Redis Cloud DB | `REDIS_HOST` `REDIS_PORT` `REDIS_USERNAME` `REDIS_PASSWORD` `REDIS_SSL` |
| **RDI backend** (streams + processor state) | Redis Enterprise `rdidb` inside the GKE `rdi` namespace | Created by `terraform/scripts/install-rdi.sh`; not the target DB |

Do not point RDI's backend at the iris-demos database. A `FLUSHDB` there would also wipe processor state if you had combined them; `make flush-redis DOMAIN=meeting-intel` is refused on purpose.

## Embeddings

Existing domains in this repo embed **client-side** in `data_generator.py`. Context Surfaces does **not** embed at index time (no Embedder backend on import).

RDI therefore writes JSON **without** vectors. `schema.py` still declares `summary_embedding` / `text_embedding` so the Context Surface index can use them after:

```bash
make mi-embed-sidecar
```

That process `JSON.SET`s only the embedding path (a field RDI does not own, so one-writer-per-key still holds). JSONL smoke data includes deterministic fake embeddings so `make smoke-domain` does not need OpenAI.

## Local Postgres (optional)

GKE terraform already runs an in-cluster Debezium Postgres seeded from `00-schema.sql` + `01-seed.sql`. Use local Compose only when iterating on SQL without a cluster:

```bash
make mi-pg-up    # docker compose: Postgres 5432, pgAdmin 8888
make mi-pg-down
```

Image: `debezium/postgres:15-alpine` with `wal_level=logical`. Publication `meeting_intel_pub` covers all ten tables. Replication user: `dbzuser` / `dbz`.

When RDI runs on GKE, the pipeline source host must be `postgres.meeting-intel.svc.cluster.local` (the default in `deploy_pipeline.py`). Agent write tools on a laptop need `make mi-pg-forward` so `MEETING_INTEL_PG_HOST=127.0.0.1` reaches that same database.

## GKE RDI (this is the runtime the workshop uses)

Terraform lives in `terraform/`. It sizes a **3 × e2-standard-4** zonal GKE cluster (~12 vCPU / 48 GB / 100 GB disk per node), installs Redis Enterprise as RDI's backend DB, Helm-installs RDI, and stands up in-cluster Postgres seeded from `00-schema.sql` + `01-seed.sql`. The pipeline **target** is the Redis Cloud DB from `.env`.

A Cloud Agent with a project-scoped service account could `terraform plan` but **`apply` failed closed on IAM**. User Application Default Credentials on a laptop succeeded (cluster `meeting-intel-rdi`, CDC measured below). The Cloud Agent error was:

```
Error: Error when reading or editing Project Service : Request `List Project Services` returned error: ...
googleapi: Error 403: Permission denied to list services for consumer container
permission: serviceusage.services.list
reason: AUTH_PERMISSION_DENIED
  with google_project_service.container (gke.tf)
  with google_project_service.compute (gke.tf)
```

Prefer user ADC (`gcloud auth application-default login`) over that SA unless those roles are granted. Optional GCS backend: copy `terraform/backend.tf.example` to `backend.tf` (gitignored) and `terraform init -reconfigure`. Then:

```bash
export TF_VAR_project_id=your-gcp-project
# GOOGLE_APPLICATION_CREDENTIALS must be a key *file path*, not JSON contents
make generate-data DOMAIN=meeting-intel
make mi-rdi-deploy     # terraform apply + install-rdi.sh
export RDI_API_URL=http://<rdi-api-ingress-ip>
# jwtKey in generated/rdi-values.yaml signs JWTs; it is not the Bearer token.
# Login with the RDI backend Redis password (secret rdi-sys-config / RDI_REDIS_PASSWORD):
export RDI_PASSWORD=...   # then deploy_pipeline.py POSTs /api/v1/login
make mi-rdi-pipeline
make mi-verify
```

Helm provider is pinned to `>= 2.14.0, < 3.0.0` (`terraform/versions.tf`). Helm 3.x rejects the nested `kubernetes { }` block in `providers.tf`.

GKE Postgres must set `PGDATA` to a subdirectory: a zonal PD mount includes `lost+found`, and `initdb` refuses a non-empty data dir.

Required secrets / identity are also listed at the bottom of `domains/meeting-intel/README.md`. Do not commit `terraform.tfstate`, `backend.tf`, `generated/kubeconfig`, or `generated/rdi-values.yaml`.

## Makefile

| Target | What it does |
|---|---|
| `make mi-pg-up` | Local Docker Postgres + seed |
| `make mi-rdi-deploy` | GKE + RDI terraform apply |
| `make mi-rdi-pipeline` | Deploy `pipeline-config.yaml` + `jobs/` via RDI API |
| `make mi-verify` | Postgres counts == Redis prefix counts; CDC latency probe |
| `make mi-reset` | Re-seed Postgres, RDI pipeline reset (re-snapshot) |
| `make mi-embed-sidecar` | Fill vector fields on RDI JSON docs |
| `make setup DOMAIN=meeting-intel` | Full path (skips JSONL load and Redis flush) |

## Demo: initial load vs deltas (do not FLUSHDB)

The iris-demos Redis Cloud DB is the **target**. It may already hold other demo keys, Context Surface indexes, LangCache, and memory. `FLUSHDB` would wipe all of that. RDI does not need an empty database: it upserts JSON at known prefixes (`project:`, `meeting:`, `action:`, …).

**Initial load (snapshot).** First pipeline deploy already ran `snapshot.mode: initial`. To *re-show* a bulk load without flushing Redis:

```bash
make mi-pg-forward          # another terminal; write path to in-cluster Postgres
export RDI_API_URL=http://<rdi-api-ingress-ip>
export RDI_PASSWORD=...     # rdi-sys-config RDI_REDIS_PASSWORD, not jwtKey
make mi-reset               # re-apply 00-schema.sql + 01-seed.sql, then POST /pipelines/reset
make mi-verify              # wait until prefix counts match again
```

Watch Redis: the same ids (`project:proj-platform`, `meeting:mtg-2026-09-09-platform`, …) are rewritten from Postgres. That is the snapshot. RDI will not snapshot again until you reset.

**Deltas (CDC).** Leave the pipeline in `state: cdc`. Change only Postgres:

```bash
psql "host=127.0.0.1 user=postgres dbname=postgres" \
  -f domains/meeting-intel/rdi/source-db/scripts/demo/add-overdue-action.sql
# Redis: JSON.GET action:act-cdc-live-overdue
psql "host=127.0.0.1 user=postgres dbname=postgres" \
  -f domains/meeting-intel/rdi/source-db/scripts/demo/mark-action-done.sql
# same key, status becomes done
```

`make mi-verify` also inserts `act-verify-latency` and waits for `action:act-verify-latency` (then deletes the Postgres row).

## Reset

`make mi-reset` is the snapshot replay above. Do not `FLUSHDB` the target.

## Known failure modes

| Symptom | Likely cause |
|---|---|
| RDI pods crash-loop | Cluster too small. Need ≥ 4 CPU / 8 GB dedicated; GKE default here is 3×e2-standard-4. |
| Snapshot stuck | Source host wrong. From GKE use `postgres.meeting-intel.svc.cluster.local`, not `localhost`. Publication must include all 10 tables. |
| Pipeline deploy 401 | `api.jwtKey` is not the Bearer token. `POST /api/v1/login` with `RDI_PASSWORD` from secret `rdi-sys-config`. |
| Postgres CrashLoop `lost+found` | Set `PGDATA=/var/lib/postgresql/data/pgdata` (see `terraform/k8s/postgres.yaml`). |
| Redis keys exist as Hash | Job missing `data_type: json`. Context Surface indexes JSON only. |
| Keys look like `public.meetings.pk` | Job missing explicit key expression. |
| Counts mismatch after flush | `FLUSHDB` wiped RDI keys; run `make mi-reset`. |
| `agendas.ai_agenda` missing | NULL in Postgres should become JSON null/absent, not the string `"null"`. |
| Team user sees Nimbus Auth | Filter `visibility=leadership` for `access_role=team`. |
| Write tool updates Redis directly | Bug: writes must go to Postgres. |

## CDC latency

Recorded by `make mi-verify` (insert `act-verify-latency` → wait for `action:act-verify-latency`). Write the number here after the first successful GKE run:

```
CDC insert → Redis key: 4475 ms (2026-09-07, GKE meeting-intel-rdi / us-central1-a, first successful laptop apply)
```

## References vendored from

- `redis-developer/postgres-to-redis-rdi-demo` (Compose pattern, Helm deploy scripts, job JSON syntax)
- Official RDI install-on-Kubernetes + job-file docs
- `rdi-quickstart-postgres` only for `wal_level=logical` / publication / `dbzuser`
