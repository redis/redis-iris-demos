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

### Checkpoint — apply blocked on IAM (credentials are not enough)

A follow-up agent **did** have `GOOGLE_CREDENTIALS`, `TF_VAR_project_id`, `REDIS_*`, plus `gcloud` / `terraform` / `kubectl` / `helm`. `GOOGLE_APPLICATION_CREDENTIALS` was a file path. `terraform plan` succeeded. **`make mi-rdi-deploy` / `terraform apply` was not faked** — it failed on the first resources:

- `google_project_service.container` and `google_project_service.compute`
- HTTP 403 `AUTH_PERMISSION_DENIED` for `serviceusage.services.list`

The same service account also cannot `container.clusters.list`, `compute.zones.get`, or `resourcemanager.projects.get`. No GKE cluster was created. Local terraform state has only `data.google_client_config.default`.

Grant these roles on the project in `TF_VAR_project_id` (then re-run `make mi-rdi-deploy`):

| Name | Why |
|---|---|
| GCP project id (`TF_VAR_project_id` or `terraform.tfvars`) | GKE cluster |
| `GOOGLE_APPLICATION_CREDENTIALS` = path to SA key file (never the JSON blob) | Provider auth |
| IAM: `roles/serviceusage.serviceUsageAdmin`, `roles/container.admin`, `roles/compute.admin`, `roles/iam.serviceAccountUser` | Enable APIs + create cluster + node pool |
| APIs: `container.googleapis.com`, `compute.googleapis.com` | Terraform enables if `serviceusage` is allowed |
| `kubectl` + `helm` + `gke-gcloud-auth-plugin` | `install-rdi.sh` |
| `REDIS_HOST` `REDIS_PORT` `REDIS_USERNAME` `REDIS_PASSWORD` `REDIS_SSL` | Pipeline **target** |
| `RDI_API_URL` + `RDI_API_TOKEN` after install | Non-interactive pipeline deploy |
| Optional: `MEETING_INTEL_PG_*` if Postgres is port-forwarded for write tools | Agent writes |

Do **not** create a second Redis Cloud DB for application data. RDI's **backend** DB is Redis Enterprise inside GKE (`rdidb`). The **target** is the existing iris-demos Redis Cloud instance.

## Embedding decision

Client-side embeddings (this repo's pattern). Sidecar: `make mi-embed-sidecar`. Details in `rdi/README.md` section Embeddings.
