# Domain Checklist

Use this checklist after scaffolding a domain.

## `domain.py`

- `manifest.id` matches the folder name
- `generated_models_module` and `generated_models_path` match the folder
- `output_dir` is `output/<domain-id>`
- namespace keys are unique (not shared with another domain)
- `logo_path` points to a real asset under `domains/<domain-id>/assets/`
- `branding.starter_prompts` has 4-5 entries (2 Context, 2 Memory, 1 Cached)
- `branding.demo_steps` has exactly 4 entries
- identity defaults (`default_id`, `default_name`, `default_email`) match the first user in `data_generator.py`
- `identity.id_field` matches the domain's primary ID field (e.g. `"patient_id"`, `"customer_id"`)
- `get_internal_tool_definitions` returns at least `get_current_user_profile`, `get_current_time`, and `dataset_overview`
- `execute_internal_tool` handles all defined tool names and returns dicts
- if domain ID has hyphens, sub-modules are loaded via `importlib` (see `domains/radish-bank/domain.py`)

## `schema.py`

- every entity has a unique `class_name`
- every entity has a unique `file_name`
- Redis key templates use the domain namespace prefix
- vector fields declare `vector_dim` and `distance_metric`
- no `index="tag"` on fields with numeric `type_hint` (int/float) — validator rejects this
- exactly one entity has a vector embedding field (for RAG)
- `rag.index_name_contains` matches the RAG entity's `class_name` lowercased

## `prompt.py`

- includes a rule that all `filter_*` / `search_*` MCP tools take a `value` parameter (without this, the LLM passes field names as parameter keys and tools fail silently)
- includes tool discovery hints using the dynamic `tool_names` set pattern (see `domains/reddash/prompt.py` lines 7-24)
- includes common workflows (3-5 tool-call sequences)
- instructs the agent to call `get_current_user_profile` first
- memory block is conditional on `memory_enabled`
- response style section includes good/bad examples and domain-appropriate tone

## `data_generator.py`

- `DEMO_USER_ID` matches `manifest.identity.default_id`
- writes all files declared by the schema (one JSONL per entity)
- returns `GeneratedDataset` with `output_dir`, `env_updates`, `summary`
- `update_env_file` defaults to `False`; only `main()` passes `True`
- updates demo identity env vars when `update_env_file=True`
- timestamps are relative to `datetime.now(timezone.utc)` so data stays fresh
- embedding helper falls back to `fake_embedding` when no `OPENAI_API_KEY` (see `domains/reddash/data_generator.py` lines 32-44)
- creates records that support the documented flagship demo paths
- uses realistic names, amounts, and scenarios — not placeholder text

## Guardrail Routes (in `domain.py` manifest)

- `guardrail` has a `GuardrailConfig` with two routes (allowed + off-topic)
- on-topic route has 20-55 references written in real customer language (first person, casual)
- on-topic route includes conversational fillers: "Yes", "No", "Sure", "Thanks", "Hello", "Tell me more", "OK", "Got it"
- on-topic references cover: status inquiries, history lookups, complaints, recommendations, preferences, policy questions, account info
- off-topic route has 15-20 references (weather, jokes, homework, coding, etc.)
- off-topic route includes 2-3 domain-adjacent off-topic phrases (e.g., healthcare: "Can you diagnose my symptoms?")
- on-topic `distance_threshold` is 0.7, off-topic is 0.5

## Seed Data (in `domain.py` manifest)

- `seed_memories` has at least 2 entries with relevant `topics`
- seed memories are specific and actionable ("Prefers contactless delivery" not "Likes good service")
- seed memories connect to demo paths (enable the memory recall demo step)
- `seed_langcache` has at least 1 entry with a realistic prompt/response pair
- seed langcache `prompt` is semantically close to a "Cached" starter prompt card
- seed langcache `response` uses markdown **bold** for key facts and includes specific numbers
- `branding.theme.landing_bg` is a hex color matching the domain palette

## Landing Page Backgrounds

- `frontend/public/backgrounds/<domain-id>/left.svg` exists
- `frontend/public/backgrounds/<domain-id>/right.svg` exists
- SVGs are flat style, under 35KB, domain-relevant illustrations
- Objects fade toward center to keep focus on the UI

## `docs/demo_paths.md`

- includes at least two realistic conversation paths
- references real products, stores, orders, or policies from the generated data
- paths cover Context Retriever, Memory, and optionally LangCache pillars

## `presentations/` (optional)

- any domain-specific deck lives under `domains/<domain-id>/presentations/`
- deck assets are copied into the domain folder instead of referencing files from `~/Desktop`, `~/Downloads`, or another repo
- a short local run note exists if the presentation needs a static server

## Validation Commands

```bash
uv run python scripts/validate_domain.py --domain <domain-id>
uv run python scripts/generate_models.py --domain <domain-id>
uv run python scripts/smoke_domain.py --domain <domain-id>
pytest
```
