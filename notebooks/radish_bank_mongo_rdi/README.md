# Radish Bank MongoDB RDI Workshop

This folder contains the notebook and credential template for the local MongoDB to Redis Data Integration to Redis Iris workshop.

From the repo root:

```bash
uv sync --extra notebook
cp notebooks/radish_bank_mongo_rdi/.env.example notebooks/radish_bank_mongo_rdi/.env
# Fill notebooks/radish_bank_mongo_rdi/.env with Redis/OpenAI/Iris values.
uv run --extra notebook python notebooks/radish_bank_mongo_rdi/seed_mongo.py
uv run --extra notebook jupyter notebook notebooks/radish_bank_mongo_rdi/rdi_to_iris_workshop.ipynb
```

Run `seed_mongo.py` before opening the notebook. It starts the local MongoDB replica set, regenerates the Radish Bank JSONL data, and replaces the MongoDB source collections that RDI will read.

The same command also writes a readable record inventory to `output/radish-bank/mongo_seed_inventory.md`. That file is generated output and is ignored by git. To regenerate the inventory from live MongoDB without reseeding:

```bash
uv run --extra notebook python notebooks/radish_bank_mongo_rdi/export_seed_inventory.py
```

The local `.env` file is ignored by git. Keep real Redis Cloud, OpenAI, Context Retriever, Agent Memory, and LangCache secrets there.

See [context_surface_setup.md](context_surface_setup.md) for the Context Retriever admin key, surface ID, MCP agent key, and entity model setup flow.
