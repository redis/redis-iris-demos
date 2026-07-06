# Redis Iris Workshops

Hands-on notebooks for Redis Iris demos.

## Notebooks

| Notebook | Focus | Colab |
|----------|-------|-------|
| `radish_bank_workshop.ipynb` | Context Retriever + Agent Memory + LangCache | [Open](https://colab.research.google.com/github/redis/redis-iris-demos/blob/main/notebooks/radish_bank_workshop.ipynb) |
| `rdi_to_iris_workshop.ipynb` | Radish Bank local MongoDB → Redis Data Integration → Redis Iris | [Open](https://colab.research.google.com/github/redis/redis-iris-demos/blob/main/notebooks/rdi_to_iris_workshop.ipynb) |

## Run

| Where | How |
|-------|-----|
| **Colab** | Open a notebook badge → run all. Clone cell runs automatically. Paste keys into `WORKSHOP_CONFIG`. |
| **Local** | Run `uv sync --extra notebook`, then `uv run --extra notebook jupyter notebook`. Open a notebook from `notebooks/`, skip the Colab clone cell, and paste keys into `WORKSHOP_CONFIG`. |

For the Radish Bank MongoDB/RDI workshop, use the repo-managed `uv` Jupyter
environment locally. Do not run it in a shared/global Python kernel; package
versions from other notebooks can conflict with the demo stack.

## Files

- `radish_bank_workshop.ipynb` — Radish Bank Iris workshop
- `rdi_to_iris_workshop.ipynb` — Radish Bank local MongoDB RDI-to-Iris workshop
- `workshop_helpers.py` — setup, seeding, chat loop
- `workshop_data/` — JSONL demo data
- `mongo_local/docker-compose.yml` — local MongoDB replica set for RDI/change-stream demos
