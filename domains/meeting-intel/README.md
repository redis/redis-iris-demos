# Minutes (`meeting-intel`)

Harborline meeting intelligence demo. **Postgres is the system of record.** RDI syncs rows into Redis JSON. The Minutes agent reads via Context Retriever and writes back through Postgres (`save_ai_agenda`, `create_action_item`, `update_action_item_status`, `extract_from_transcript`).

Branding name: **Minutes**. Company: Harborline.

## Why this domain is different

Other packs generate JSONL and `import_data` into Redis. This pack must not do that: RDI owns every synced key. `manifest.data_plane = "rdi"` makes `make load-data` a no-op and `make flush-redis DOMAIN=meeting-intel` fail closed.

## Quick path (once GKE + RDI are up)

```bash
make generate-data DOMAIN=meeting-intel
make validate-domain DOMAIN=meeting-intel
make generate-models DOMAIN=meeting-intel
make smoke-domain DOMAIN=meeting-intel
# After GCP/GKE/RDI (see rdi/README.md):
make setup DOMAIN=meeting-intel
DEMO_DOMAIN=meeting-intel make dev
```

## Demo user

| Env | Default |
|---|---|
| `DEMO_USER_ID` | `person-maya` |
| `DEMO_USER_NAME` | Maya Chen |
| `DEMO_USER_EMAIL` | maya.chen@harborline.example |
| `DEMO_USER_ROLE` | `team` (set `leadership` + `person-dana` to see freeze / Nimbus Auth) |

## Scripted paths

See [`docs/demo_paths.md`](docs/demo_paths.md).

## RDI / GKE

See [`rdi/README.md`](rdi/README.md). Terraform: [`rdi/terraform/`](rdi/terraform/).

A Cloud Agent SA could plan but could not apply (`serviceusage.services.list` 403). Laptop user ADC created cluster `meeting-intel-rdi`; first CDC probe was **4475 ms**. Do not `FLUSHDB` the iris-demos Redis Cloud target — replay snapshot with `make mi-reset`, then show deltas with the SQL under Path 5 in `docs/demo_paths.md`.

| Name | Why |
|---|---|
| GCP project id (`TF_VAR_project_id` or `terraform.tfvars`) | GKE cluster |
| `GOOGLE_APPLICATION_CREDENTIALS` = path to SA key file (never the JSON blob) | Provider auth |
| IAM: `roles/serviceusage.serviceUsageAdmin`, `roles/container.admin`, `roles/compute.admin`, `roles/iam.serviceAccountUser` | Enable APIs + create cluster + node pool |
| APIs: `container.googleapis.com`, `compute.googleapis.com` | Terraform enables if `serviceusage` is allowed |
| `kubectl` + `helm` + `gke-gcloud-auth-plugin` | `install-rdi.sh` |
| `REDIS_HOST` `REDIS_PORT` `REDIS_USERNAME` `REDIS_PASSWORD` `REDIS_SSL` | Pipeline **target** |
| `RDI_API_URL` + `RDI_PASSWORD` (rdi-sys-config) after install | Login + pipeline deploy (`jwtKey` is not the Bearer token) |
| Optional: `MEETING_INTEL_PG_*` if Postgres is port-forwarded for write tools | Agent writes |

Do **not** create a second Redis Cloud DB for application data. RDI's **backend** DB is Redis Enterprise inside GKE (`rdidb`). The **target** is the existing iris-demos Redis Cloud instance.

## Embedding decision

Client-side embeddings (this repo's pattern). Sidecar: `make mi-embed-sidecar`. Details in `rdi/README.md` section Embeddings.
