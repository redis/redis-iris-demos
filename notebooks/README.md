# Redis Iris Workshops

Hands-on notebooks for Redis Iris demos.

## Notebooks

| Notebook | Focus | Colab |
|----------|-------|-------|
| `radish_bank_workshop.ipynb` | Context Retriever + Agent Memory + LangCache | [Open](https://colab.research.google.com/github/redis/redis-iris-demos/blob/main/notebooks/radish_bank_workshop.ipynb) |
| `radish_bank_mongo_rdi/rdi_to_iris_workshop.ipynb` | Radish Bank local MongoDB → Redis Data Integration → Redis Iris | [Open](https://colab.research.google.com/github/redis/redis-iris-demos/blob/main/notebooks/radish_bank_mongo_rdi/rdi_to_iris_workshop.ipynb) |

## Run

| Where | How |
|-------|-----|
| **Colab** | Open a notebook badge → run all. Clone cell runs automatically. Follow that notebook's credential setup cell. |
| **Local** | Run `uv sync --extra notebook`, copy any notebook-specific `.env.example` to `.env`, then run `uv run --extra notebook jupyter notebook`. Open a notebook from `notebooks/` and skip the Colab clone cell. |

For the Radish Bank MongoDB/RDI workshop, use the repo-managed `uv` Jupyter
environment locally. Do not run it in a shared/global Python kernel; package
versions from other notebooks can conflict with the demo stack.

Radish Bank MongoDB/RDI credentials should live in:

```bash
cp notebooks/radish_bank_mongo_rdi/.env.example notebooks/radish_bank_mongo_rdi/.env
```

The generated `.env` file is ignored by git.

## Files

- `radish_bank_workshop.ipynb` — Radish Bank Iris workshop
- `radish_bank_mongo_rdi/rdi_to_iris_workshop.ipynb` — Radish Bank local MongoDB RDI-to-Iris workshop
- `workshop_helpers.py` — setup, seeding, chat loop
- `workshop_data/` — JSONL demo data
- `mongo_local/docker-compose.yml` — local MongoDB replica set for RDI/change-stream demos
- `radish_bank_mongo_rdi/.env.example` — credential template for the MongoDB/RDI workshop
