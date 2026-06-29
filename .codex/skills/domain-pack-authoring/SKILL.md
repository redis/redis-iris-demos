---
name: domain-pack-authoring
description: Use when creating, validating, or extending demo business domains in this repo. Covers the required DomainPack contract, fixed folder layout, scaffold command, validation flow, smoke testing, and the rules for keeping framework code separate from domain-specific code.
---

# Domain Pack Authoring

Use this skill when the task is to add a new business domain, refactor an existing domain pack, or check that a domain follows the repo contract.

**Reference domains** (read these for patterns):
- `domains/reddash/` — food delivery (canonical reference for standard patterns)
- `domains/radish-bank/` — banking (custom internal tools, hyphenated domain ID)
- `domains/electrohub/` — electronics retail (rich product catalog with vector search)
- `domains/healthcare/` — patient portal (simpler entity schema)
- `domains/finance-researcher/` — market analysis (timeseries, UiConfig, watchlists)

## Workflow

1. Run `uv run python scripts/create_domain.py <domain-id>` unless the domain already exists.
2. Edit only files under `domains/<domain-id>/` unless the task explicitly changes shared framework code.
3. Fill in the required domain contract in `domains/<domain-id>/domain.py`.
4. Define entity specs in `domains/<domain-id>/schema.py`.
5. Implement prompt guidance in `domains/<domain-id>/prompt.py`.
6. Implement domain demo-data generation in `domains/<domain-id>/data_generator.py`.
7. Add or update scripted demo paths in `domains/<domain-id>/docs/demo_paths.md`.
8. If the domain includes presentation material, keep it under `domains/<domain-id>/presentations/`.
9. Add Iris-specific configuration to the manifest in `domain.py`:
   - `guardrail` — a `GuardrailConfig` with 20-55 on-topic route references + 15-20 off-topic references (see Guardrail Routes below)
   - `seed_memories` — at least 2 `SeedMemory` entries for the demo user (personal preferences the agent can recall)
   - `seed_langcache` — at least 1 `SeedLangCacheEntry` for a common question (must match a "Cached" starter prompt)
   - `branding.theme.landing_bg` — a hex color for the landing page background matching the domain's visual identity
   - `branding.demo_steps` — exactly 4 strings (Context question, Memory store, "Click Memory", Memory recall)
   - `branding.starter_prompts` — 4-5 `PromptCard` objects (2 Context, 2 Memory, 1 Cached)
10. Create landing page background SVGs under `frontend/public/backgrounds/<domain-id>/`:
    - `left.svg` (~590×817) and `right.svg` (~632×817)
    - Flat illustration style, domain-relevant objects, fade toward center
    - Use the domain's accent color palette, no text, under 35KB each
11. Run validation and smoke tests:
   `uv run python scripts/validate_domain.py --domain <domain-id>`
   `uv run python scripts/generate_models.py --domain <domain-id>`
   `uv run python scripts/smoke_domain.py --domain <domain-id>`
12. If shared framework changes were required, run repo tests before finishing.

## Required Layout

Every domain must use this structure:

```text
domains/<domain-id>/
  __init__.py
  domain.py
  schema.py
  prompt.py
  data_generator.py
  assets/logo.<svg|png|jpg|jpeg|webp>
  docs/demo_paths.md
```

Landing page backgrounds:

```text
frontend/public/backgrounds/<domain-id>/
  left.svg
  right.svg
```

Generated files:

```text
domains/<domain-id>/generated_models.py
output/<domain-id>/
```

Optional docs and collateral:

```text
domains/<domain-id>/presentations/
```

## Hyphenated Domain IDs

If the domain ID contains hyphens (e.g., `radish-bank`), Python cannot use standard imports. These domains must use `importlib` to load sub-modules. See `domains/radish-bank/domain.py` for the pattern. Prefer unhyphenated IDs when possible.

## Contract Rules

- `domains/<domain-id>/domain.py` must export `DOMAIN`.
- `DOMAIN` must satisfy the shared contract in `backend/app/core/domain_contract.py`.
- Keep branding, namespace, RAG config, and identity config declarative in `manifest`.
- `manifest.branding.logo_path` may point to any supported image asset under `domains/<domain-id>/assets/`.
- `manifest.guardrail` must define a `GuardrailConfig` with routes (see Guardrail Routes below).
- `manifest.seed_memories` must include at least 2 long-term memories for the demo user (preferences, history).
- `manifest.seed_langcache` must include at least 1 cached response. Its `prompt` must be semantically close to a "Cached" starter prompt card so the demo shows a cache hit.
- `manifest.branding.theme.landing_bg` must be a hex color that complements the domain's accent palette.
- Keep code hooks limited to:
  - `build_system_prompt`
  - `get_internal_tool_definitions`
  - `execute_internal_tool`
  - `write_dataset_meta`
  - `generate_demo_data`
  - `validate`

## Guardrail Routes

Guardrails use semantic routing via vector similarity. Reference phrases are embedded into a Redis vector index. When a user message arrives, it is embedded and compared against all references. If the closest match is the allowed route above its distance threshold, the message passes — otherwise it is blocked.

**This means references must be written in the language real customers actually use.** Formal or technical descriptions will not match casual user messages.

### On-topic route (20-55 references, `distance_threshold: 0.7`)

Cover these categories:
- **Status inquiries**: "Where is my order?", "What's the status of my referral?"
- **History lookups**: "Show me my recent orders", "What appointments have I had?"
- **Complaints/issues**: "My order arrived cold", "I was charged twice"
- **Recommendations**: "What should I order tonight?", "Which provider do you recommend?"
- **Preference management**: "Remember that I prefer...", "What do you know about me?"
- **Policy/FAQ questions**: "What's your refund policy?", "How do I schedule a follow-up?"
- **Account/profile**: "What are my account details?", "Update my delivery address"
- **Product/service info**: domain-specific product or service inquiries

**Conversational fillers must be on-topic.** Without these, simple follow-ups get blocked:
```
"Yes", "No", "Sure", "Thanks", "Hello", "Hi there", "Can you help me?",
"Tell me more", "Go ahead", "That's all, thanks", "OK", "Got it",
"Yes please", "No thanks", "What else can you help with?"
```

Write in first person — these are things a customer says:
- GOOD: "I haven't received my shipment yet"
- BAD: "Customer inquires about shipment status"

Include natural variations of the same intent:
- "Where is my order?", "What's the ETA on my delivery?", "My order hasn't arrived yet"

### Off-topic route (15-20 references, `distance_threshold: 0.5`)

Standard set (reuse across domains):
```
"What's the weather like today?", "Tell me a joke", "Help me with my homework",
"Explain quantum physics", "Write me a Python script", "Translate this to Spanish",
"Who won the Super Bowl?", "Write a poem about love", "What's the meaning of life?",
"Help me debug my React code", "Plan a vacation to Hawaii"
```

Add 2-3 domain-adjacent off-topic phrases — things that sound related but are outside scope:
- Healthcare: "Can you diagnose my symptoms?", "Should I take this medication?"
- Finance: "Should I buy this stock?", "Give me crypto trading tips"
- Food delivery: "Give me a recipe for pasta", "How many calories are in a burger?"

## Internal Tools

Every domain **must** register at least these internal tools in `get_internal_tool_definitions`:

1. **`get_current_user_profile`** — returns the signed-in user's identity (ID, name, email). Uses `manifest.identity` for env var names, defaults, and `id_field`. Set `identity.id_field` to the domain-appropriate field name (e.g. `"patient_id"`, `"customer_id"`).
2. **`get_current_time`** — returns the current UTC timestamp in ISO 8601. The agent needs this to compare against dates in the data.
3. **`dataset_overview`** — returns record counts per entity. Useful for the agent to understand the data scope.

`execute_internal_tool` must handle all three tool names and return dicts.

Optional domain-specific tools handle state-changing operations (not data retrieval — MCP tools handle that). See `domains/radish-bank/domain.py` for examples: `place_fixed_deposit`, `buy_accident_insurance`, `request_annual_card_fee_waiver`.

## Prompt Rules

The system prompt built by `prompt.py` must follow this structure (see `domains/reddash/prompt.py` for the canonical pattern):

1. **Agent identity** — one sentence defining who the agent is
2. **Available Tools** — internal tools listed first, then conditional memory tools, then MCP tool discovery hints
3. **Critical Rules** — see below
4. **Common Workflows** — 3-5 numbered tool-call sequences for key scenarios
5. **Response Style** — tone, formatting rules, good/bad examples

### The `value` parameter rule (mandatory)

This rule MUST appear in every prompt. Without it, the LLM passes field names as parameter keys (e.g. `patient_id="P001"` instead of `value="P001"`), which the MCP server rejects silently. The agent receives empty results and tells the user data is unavailable.

### Tool discovery hints

Use the dynamic pattern from `domains/reddash/prompt.py` lines 7-24: build a `tool_names` set from `mcp_tools`, then include hints only for tools that exist. This ensures the prompt stays accurate regardless of which MCP tools are available.

### Memory block

The memory tools block and memory rules are conditional on `memory_enabled`. Copy the pattern from `domains/reddash/prompt.py` lines 28-42. Instruct the agent that pre-loaded memory context is already in the conversation — `search_customer_memory` should only be called when the user explicitly asks about past preferences.

### Response style

Adapt tone to the domain (warm for food delivery, professional for healthcare, formal for banking, analytical for finance). All domains share: 2-3 sentences max, markdown **bold** for key facts, never expose internal IDs or UTC timestamps.

## Data Generation Rules

- `generate_demo_data` defaults to `update_env_file=False`. Only the `scripts/generate_data.py` pipeline and direct `main()` invocation should pass `update_env_file=True`.
- If the domain has a `main()` guard at the bottom of `data_generator.py`, it must pass `update_env_file=True` explicitly.
- `DEMO_USER_ID` must match `manifest.identity.default_id`.
- All timestamps must be relative to `datetime.now(timezone.utc)` so data stays fresh.
- The embedding helper must check for `OPENAI_API_KEY` and fall back to `fake_embedding`. Copy from `domains/reddash/data_generator.py` lines 32-44.

## Quality Bar

- Seed the domain with at least one flagship demo user and enough data to support 2-3 realistic conversation paths.
- Make starter prompts correspond to real records in the generated dataset.
- Keep the prompt focused on tool-use workflows, not generic brand copy.
- Document the flagship paths in `docs/demo_paths.md` so an agent or human can run the demo consistently.
- If you build a deck for the domain, keep links, assets, and README notes inside `domains/<domain-id>/presentations/`.

### Content realism

All text — guardrail routes, seed memories, demo data, starter prompts — must read as if written by or for a real customer of that vertical.

- Use names real people have: "Dr. Sofia Martinez", "Sakura Sushi" — not "Doctor 1", "Restaurant A"
- Use specific amounts: "$47.92", "3.1% p.a." — not "$100.00", "$50.00"
- Create interesting demo scenarios: a late order with a reason, a pending referral, an active support ticket
- Seed memories should be specific and actionable: "Prefers contactless delivery" not "Likes good service"

## Separation Rules

- Do not hard-code domain strings in `backend/app/*` or `frontend/src/*`.
- Do not add domain-specific scripts under `scripts/`; extend the generic scripts instead.
- Do not put generated models under `backend/app/context_surfaces/`; keep them inside the domain package.
- If a new requirement seems domain-specific, prefer adding it to the domain contract before touching shared runtime code.

## Stop Conditions

Do not consider the task complete if any of these remain:

- placeholder prompts
- empty `ENTITY_SPECS`
- missing logo asset
- `validate_domain.py` fails
- `smoke_domain.py` fails
- `get_internal_tool_definitions` returns an empty tuple
- system prompt is missing the `value` parameter hint for MCP tools
- `generate_demo_data` still defaults `update_env_file=True`
- generated models use `Any` as relationship type annotations (run `make generate-models DOMAIN=<id>` to regenerate)
- missing guardrail routes (no `GuardrailConfig` in manifest)
- on-topic guardrail route has fewer than 20 references
- on-topic guardrail route is missing conversational fillers (Yes, No, Sure, Thanks, Hello)
- missing seed memories (empty `seed_memories` list)
- missing seed langcache entries (empty `seed_langcache` list)
- seed langcache prompt does not match a "Cached" starter prompt card
- missing `landing_bg` in theme config
- missing landing page background SVGs (`frontend/public/backgrounds/<domain-id>/left.svg` and `right.svg`)
- starter prompts reference data that does not exist in the generator
- `branding.demo_steps` does not have exactly 4 entries
- `branding.starter_prompts` does not have 4-5 entries (2 Context, 2 Memory, 1 Cached)

## References

Read [references/checklist.md](references/checklist.md) when you need the exact file-by-file checklist.
