# Radish Bank Mongo-to-Redis Context Surface Setup

This document explains the credential flow and Context Surface setup used by the Radish Bank MongoDB to Redis Data Integration to Redis Iris workshop.

## Surface Name

The workshop Context Surface should be named:

```text
radish_bank_mongo_to_redis_context_surface
```

Use this no-space name to distinguish the MongoDB/RDI workshop surface from the generic Radish Bank demo surface.

## End-to-End Flow

The workshop uses this path:

```text
Local MongoDB source
  -> Redis Data Integration (RDI)
  -> Redis JSON keys
  -> Redis Iris Context Surface / Context Retriever MCP tools
  -> Redis Iris demo UI or notebook agent
```

RDI is responsible for moving MongoDB records into Redis. Context Retriever is responsible for exposing the Redis-backed entity model as MCP tools.

The notebook also has a fallback copy lane that writes MongoDB records to Redis JSON directly. That fallback is useful for validating the Iris/UI path when a live RDI deployment is not available, but it is not the RDI path.

## Environment File

Workshop credentials live in:

```text
notebooks/radish_bank_mongo_rdi/.env
```

That file is ignored by git. The committed template is:

```text
notebooks/radish_bank_mongo_rdi/.env.example
```

Create the local file with:

```bash
cp notebooks/radish_bank_mongo_rdi/.env.example notebooks/radish_bank_mongo_rdi/.env
```

## Context Retriever Keys

### `CTX_ADMIN_KEY`

`CTX_ADMIN_KEY` is the administrative API key for Redis Context Retriever / Context Surfaces.

It is used by the setup notebook to:

- create a new Context Surface
- update an existing Context Surface
- register the Radish Bank entity model
- configure the Redis data source connection
- create an agent-scoped MCP key

This key is powerful. Keep it in the ignored `.env` file and do not put it in the notebook, docs, git commits, or UI config.

### `CTX_SURFACE_ID`

`CTX_SURFACE_ID` is the identifier returned by Context Retriever after the surface is created.

The setup notebook starts with this blank:

```env
CTX_SURFACE_ID=
```

When the "Create the Redis Iris Context Surface" cell runs, it calls the Context Surfaces API, receives the generated surface ID, and writes it back to the ignored `.env` file:

```env
CTX_SURFACE_ID=<generated surface id>
```

On later runs, the notebook sees `CTX_SURFACE_ID` and updates that existing surface instead of creating a new one.

### `MCP_AGENT_KEY`

`MCP_AGENT_KEY` is the agent-scoped key used by the app and notebook agent to call MCP tools for this specific surface.

The setup notebook also starts with this blank:

```env
MCP_AGENT_KEY=
```

After the surface exists, the notebook creates an agent key named:

```text
radish_bank_mongo_to_redis_agent
```

It then writes the generated key back to the ignored `.env` file:

```env
MCP_AGENT_KEY=<generated agent key>
```

The demo UI and notebook agent use this key to list and call Context Retriever MCP tools. They do not need `CTX_ADMIN_KEY`.

## Entity Model Setup

The Context Surface is not just a credential container. It also registers the entity model that Context Retriever uses to generate tools.

The notebook builds the model from the Radish Bank domain pack:

```text
domains/radish-bank/schema.py
domains/radish-bank/generated_models.py
domains/radish-bank/domain.py
```

The current entity set is:

```text
Customer
Account
Card
FixedDepositPlan
InsurancePlan
Branch
BranchHours
ProductHolding
ServiceRequest
BankDocument
```

Each entity defines:

- the Redis key pattern, for example `radish_bank_account:{account_id}`
- key fields
- indexed fields
- vector fields, where applicable
- relationships to other entities

Context Retriever turns this model into MCP tools such as:

```text
filter_account_by_customer_id
filter_card_by_customer_id
filter_bankdocument_by_category
find_fixeddepositplan_by_rate_percent_range
vector_search_bankdocument_content_embedding
```

The tools exist as soon as the surface is active. They return useful data only after Redis contains the expected `radish_bank_*` JSON records.

## Redis Data Source

The Context Surface points at the same Redis database that RDI writes into.

The relevant `.env` values are:

```env
REDIS_HOST=
REDIS_PORT=
REDIS_USERNAME=default
REDIS_PASSWORD=
REDIS_SSL=false
REDIS_DB=0
```

For the current workshop database, `REDIS_SSL=false` is required because the endpoint accepts a non-TLS Redis connection. If a future Redis Cloud database requires TLS, set `REDIS_SSL=true` and recreate or update the surface.

## Setup Sequence

1. Fill Redis, OpenAI, Memory, LangCache, and `CTX_ADMIN_KEY` in `notebooks/radish_bank_mongo_rdi/.env`.
2. Seed the local MongoDB source before opening the notebook:

   ```bash
   uv run --extra notebook python notebooks/radish_bank_mongo_rdi/seed_mongo.py
   ```

   This starts the bundled MongoDB replica set, regenerates Radish Bank JSONL data, and replaces the MongoDB source collections that RDI will read.

3. Leave these blank initially:

   ```env
   CTX_SURFACE_ID=
   MCP_AGENT_KEY=
   ```

4. Run the notebook through the Context Surface creation cell.
5. The notebook creates or updates `radish_bank_mongo_to_redis_context_surface`.
6. The notebook creates the `radish_bank_mongo_to_redis_agent` key if `MCP_AGENT_KEY` is blank.
7. The notebook writes `CTX_SURFACE_ID` and `MCP_AGENT_KEY` back to the ignored `.env`.
8. Run RDI so MongoDB records arrive in Redis as `radish_bank_*` JSON keys:

   ```bash
   redis-di deploy --dir notebooks/generated_rdi_pipeline/radish-bank-mongodb-local
   ```

9. Start the demo UI with `DEMO_DOMAIN=radish-bank` and the same `.env` values.

## Current Verification Commands

Check that Redis is reachable:

```bash
uv run --extra notebook python - <<'PY'
import os
from pathlib import Path
from dotenv import load_dotenv
from redis import Redis

ROOT = Path.cwd()
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "notebooks/radish_bank_mongo_rdi/.env", override=True)

client = Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME") or "default",
    password=os.environ["REDIS_PASSWORD"],
    db=int(os.environ.get("REDIS_DB") or 0),
    ssl=(os.environ.get("REDIS_SSL", "false").lower() == "true"),
    decode_responses=True,
)
print(client.ping())
PY
```

Check that MCP tools are visible:

```bash
uv run --extra notebook python - <<'PY'
import asyncio
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path.cwd()
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "notebooks/radish_bank_mongo_rdi/.env", override=True)

from backend.app.settings import get_settings
from backend.app.context_surface_service import ContextSurfaceService

async def main():
    service = ContextSurfaceService(get_settings())
    try:
        tools = await service.list_tools()
        print(f"MCP tools visible: {len(tools)}")
        for tool in tools[:10]:
            print("-", tool.get("name"))
    finally:
        await service.close()

asyncio.run(main())
PY
```

Check whether RDI has populated Redis:

```bash
uv run --extra notebook python - <<'PY'
import os
from pathlib import Path
from dotenv import load_dotenv
from redis import Redis

ROOT = Path.cwd()
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "notebooks/radish_bank_mongo_rdi/.env", override=True)

client = Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.environ.get("REDIS_USERNAME") or "default",
    password=os.environ["REDIS_PASSWORD"],
    db=int(os.environ.get("REDIS_DB") or 0),
    ssl=(os.environ.get("REDIS_SSL", "false").lower() == "true"),
    decode_responses=True,
)

for prefix in [
    "radish_bank_customer:",
    "radish_bank_account:",
    "radish_bank_card:",
    "radish_bank_fd_plan:",
    "radish_bank_document:",
]:
    count = sum(1 for _ in client.scan_iter(match=prefix + "*", count=500))
    print(f"{prefix} {count}")
PY
```

If the MCP tools are visible but the `radish_bank_*` counts are zero, the Context Surface is set up but the data ingestion path has not populated Redis yet.
