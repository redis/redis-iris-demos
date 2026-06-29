# Domain Pack Authoring

Use this skill when the task is to **create a new business domain**, extend an existing domain, or validate that a domain follows the repo contract. A "domain" is a vertical (e.g., food delivery, healthcare, banking) with its own branding, data schema, agent prompt, guardrails, seed data, and frontend assets.

**Reference domains** (read these for patterns):
- `domains/reddash/` — food delivery support (canonical reference for standard patterns)
- `domains/radish-bank/` — banking (reference for custom internal tools, hyphenated domain ID)
- `domains/electrohub/` — electronics retail (reference for rich product catalog with vector search)
- `domains/healthcare/` — patient portal (reference for simpler entity schema)
- `domains/finance-researcher/` — market analysis (reference for timeseries, UiConfig, watchlists)

**Contract definition**: `backend/app/core/domain_contract.py` (all Pydantic models)
**Entity schema types**: `backend/app/core/domain_schema.py` (EntitySpec, FieldSpec, RelationshipSpec)

---

## Workflow

1. **Scaffold**: `uv run python scripts/create_domain.py <domain-id>`
2. **Design entities** in `domains/<domain-id>/schema.py`
3. **Fill the manifest** in `domains/<domain-id>/domain.py` — branding, namespace, identity, rag, guardrail, seeds
4. **Write the system prompt** in `domains/<domain-id>/prompt.py`
5. **Implement internal tools** in `domain.py` — definitions + execution
6. **Build data generator** in `domains/<domain-id>/data_generator.py`
7. **Generate models**: `uv run python scripts/generate_models.py --domain <domain-id>`
8. **Generate demo data**: `uv run python scripts/generate_data.py --domain <domain-id>`
9. **Create frontend assets** — logo SVG + landing page background SVGs
10. **Write demo paths** in `domains/<domain-id>/docs/demo_paths.md`
11. **Validate**: `uv run python scripts/validate_domain.py --domain <domain-id>`
12. **Smoke test**: `uv run python scripts/smoke_domain.py --domain <domain-id>`

After validation passes: `make setup DOMAIN=<domain-id> && make dev` to test end-to-end.

---

## Required File Layout

```
domains/<domain-id>/
  __init__.py
  domain.py              # Manifest + DomainPack implementation
  schema.py              # EntitySpec definitions
  prompt.py              # System prompt builder
  data_generator.py      # Synthetic data generation
  assets/logo.<svg|png>  # Domain logo
  docs/demo_paths.md     # Scripted demo walkthrough

frontend/public/backgrounds/<domain-id>/
  left.svg               # Landing page left illustration (~590x817)
  right.svg              # Landing page right illustration (~632x817)

# Auto-generated (do not edit):
domains/<domain-id>/generated_models.py
output/<domain-id>/
```

`domain.py` must export a module-level `DOMAIN` object satisfying the `DomainPack` protocol.

---

## Entity Schema (`schema.py`)

Each domain defines `ENTITY_SPECS: tuple[EntitySpec, ...]` — the Redis data schema.

### Entity design pattern

Every domain follows this hierarchy:

1. **Primary user** — Customer, Patient, AnalystProfile (1 entity)
2. **Transactional entities** — Order, Appointment, ServiceRequest (2-4 entities linking user to actions)
3. **Reference/lookup entities** — Restaurant, Provider, Branch, Store (1-3 entities)
4. **Supporting entities** — OrderItem, DeliveryEvent, ShipmentEvent (2-4 detail entities)
5. **RAG document entity** — Policy, HealthDoc, BankDocument, Guide (1 entity with vector embeddings)

Total: typically 7-11 entities per domain.

### FieldSpec rules

```python
FieldSpec(
    name="order_id",          # Snake_case field name
    type_hint="str",          # Python type: str, int, float, list[str]
    description="...",        # Human description (used in MCP tool descriptions)
    index="tag",              # Index type: "tag", "text", "numeric", "vector", or None
    weight=2.0,               # Text search relevance weight (default 1.0)
    no_stem=True,             # Disable stemming (use for emails, IDs)
    sortable=True,            # Enable sorting (use for numeric fields)
    is_key_component=True,    # This field is the entity's primary key
    vector_dim=1536,          # Vector dimension (required for index="vector")
    distance_metric="cosine", # Vector distance (required for index="vector")
)
```

**Index type guidance:**
- `"tag"` — Exact match filtering. Use for IDs, status enums, categories. NEVER use with numeric type_hints (int/float) — the validator rejects this because Redis TAG fields cannot index numeric JSON values.
- `"text"` — Full-text search with stemming. Use for names, descriptions, summaries.
- `"numeric"` — Range queries and sorting. Use for prices, ratings, quantities.
- `"vector"` — Vector similarity search. Use for embedding fields. Always set `vector_dim=1536` and `distance_metric="cosine"`.
- `None` — Not indexed. Use for non-searchable metadata.

**Key template pattern:** `{domain_prefix}_{entity_lowercase}:{id_field}` — e.g., `reddash_order:{order_id}`, `healthcare_appointment:{id}`.

**Relationship specs** link entities: `RelationshipSpec(name="orders", description="...", source_field="customer_id", target_type="Order")`. The `source_field` must exist on the entity, and `target_type` must match another entity's `class_name`.

### RAG document entity

Every domain needs exactly one entity with a vector embedding field for RAG search. This entity stores domain documents (policies, FAQs, guides). Pattern:

```python
EntitySpec(
    class_name="Policy",  # or HealthDoc, BankDocument, Guide
    redis_key_template="reddash_policy:{policy_id}",
    file_name="policies.jsonl",
    id_field="policy_id",
    fields=(
        FieldSpec(name="policy_id", type_hint="str", description="...", index="tag", is_key_component=True),
        FieldSpec(name="title", type_hint="str", description="...", index="text", weight=2.0),
        FieldSpec(name="category", type_hint="str", description="...", index="tag"),
        FieldSpec(name="content", type_hint="str", description="...", index="text"),
        FieldSpec(name="content_embedding", type_hint="list[float]", description="...",
                  index="vector", vector_dim=1536, distance_metric="cosine"),
    ),
)
```

---

## Domain Manifest (`domain.py`)

The manifest is a `DomainManifest` containing all domain configuration. Every field below must be filled thoughtfully.

### BrandingConfig

```python
BrandingConfig(
    app_name="Reddash",                    # Display name in topbar
    subtitle="Delivery Support",           # Below app name
    hero_title="How can we help?",         # Landing page headline
    placeholder_text="Ask about your order, delivery status, or policies...",
    logo_path="domains/reddash/assets/logo.svg",
    demo_steps=[...],                      # 4-step guided demo
    starter_prompts=[...],                 # 4-5 prompt cards
    theme=ThemeConfig(...),
)
```

**demo_steps** — exactly 4 strings that walk through the flagship demo:
1. A Context Retriever question (exercises MCP tools)
2. A Memory Store request ("Please remember that I prefer...")
3. "Click Memory" (instructs user to open the memory panel)
4. A Memory Recall question ("Given what you know about me...")

**starter_prompts** — 4-5 `PromptCard` objects. Each has:
- `eyebrow`: Category label — use "Context" (exercises MCP tools), "Memory" (exercises memory), or "Cached" (matches a seed_langcache entry)
- `title`: Short label (e.g., "Track my order", "Save preferences")
- `prompt`: The actual message sent to the agent

Distribution: 2 Context cards, 2 Memory cards (1 store + 1 recall), 1 Cached card. The Cached card's prompt must closely match a `seed_langcache` entry so the demo shows a cache hit.

**Important:** Starter prompt messages must reference real records from the generated demo data. "Show me my order history" works because the data generator creates orders for the demo user. "Track order ORD-99999" fails if that ID doesn't exist.

### ThemeConfig

All colors are hex strings. The most important is `landing_bg` — the landing page background color. Choose a light, warm color that complements the domain's accent color. Examples:
- Reddash (red accent): warm peachy `#FFF3D9`
- Healthcare (blue accent): soft blue `#E8F4FD`
- Radish Bank (green accent): soft green `#E8F5E9`

### NamespaceConfig

Derive all prefixes from the domain ID:

```python
NamespaceConfig(
    redis_prefix="<domain-id>",
    dataset_meta_key="<domain-id>:meta:dataset",
    checkpoint_prefix="<domain-id>:checkpoints:",
    checkpoint_write_prefix="<domain-id>:checkpoint_writes:",
    redis_instance_name="<Display Name> Redis",
    surface_name="<Display Name> Context Surface",
    agent_name="<Display Name> Agent",
)
```

### RagConfig

```python
RagConfig(
    tool_name="vector_search_<rag_entity_plural>",  # e.g., "vector_search_policies"
    status_text="Searching <entity> via vector similarity...",
    generating_text="Generating answer from <entity>...",
    index_name_contains="<rag_entity_classname_lowercase>",  # MUST match the RAG entity's class_name lowercased
    vector_field="content_embedding",
    return_fields=["title", "category", "content"],
    num_results=3,
    answer_system_prompt="You are the <domain> assistant. Answer using only the retrieved documents. If they do not cover the question, say so briefly.",
)
```

The `index_name_contains` value is used to find the correct RediSearch index at runtime. It must be a lowercase substring of the RAG entity's class_name. Examples: "policy" for Policy, "healthdoc" for HealthDoc, "guide" for Guide.

### IdentityConfig

```python
IdentityConfig(
    tool_name="get_current_user_profile",
    id_field="customer_id",        # Domain-appropriate: "patient_id", "analyst_id", etc.
    default_id="CUST_DEMO_001",    # Must match the first user created by data_generator.py
    default_name="Alex Rivera",    # Must match
    default_email="alex.rivera@example.com",
    description="Returns the signed-in customer's ID, name, and email.",
)
```

### GuardrailConfig

Guardrails use semantic routing via vector similarity. Reference phrases are embedded and stored in a Redis vector index. When a user message arrives, it's embedded and compared against all references. If the closest match is the allowed route above its distance threshold, the message passes. Otherwise it's blocked.

**This means references must be written in the language real customers actually use.** They are compared via vector similarity — formal or technical language won't match casual user messages.

```python
GuardrailConfig(
    router_name="<domain-id>-guardrails",
    allowed_route_name="<domain_topic>",  # e.g., "food_delivery", "healthcare", "banking"
    routes=[
        GuardrailRouteConfig(
            name="<domain_topic>",
            references=[...],  # 20-55 on-topic phrases
            distance_threshold=0.7,
        ),
        GuardrailRouteConfig(
            name="off_topic",
            references=[...],  # 15-20 off-topic phrases
            distance_threshold=0.5,
        ),
    ],
)
```

#### Writing on-topic route references (20-55 phrases)

Cover these categories for ANY domain:

1. **Status inquiries** — "Where is my order?", "What's the status of my referral?"
2. **History lookups** — "Show me my recent orders", "What appointments have I had?"
3. **Complaints/issues** — "My order arrived cold", "I was charged twice"
4. **Recommendations** — "What should I order tonight?", "Which provider do you recommend?"
5. **Preference management** — "Remember that I prefer...", "What do you know about me?"
6. **Policy/FAQ questions** — "What's your refund policy?", "How do I schedule a follow-up?"
7. **Account/profile** — "What are my account details?", "Update my delivery address"
8. **Product/service info** — "What laptops do you have?", "What are your FD rates?"

**Critical: Include conversational fillers as on-topic references.** Without these, simple follow-ups get blocked:
```python
"Yes", "No", "Sure", "Thanks", "Hello", "Hi there", "Can you help me?",
"Tell me more", "Go ahead", "That's all, thanks", "OK", "Got it",
"Yes please", "No thanks", "What else can you help with?",
```

**Write in first person** — these are things a customer says:
- GOOD: "I haven't received my shipment yet"
- BAD: "Customer inquires about shipment status"

**Include natural variations** of the same intent:
- "Where is my order?", "What's the ETA on my delivery?", "My order hasn't arrived yet", "Is my food on the way?"

#### Writing off-topic route references (15-20 phrases)

Standard set (reuse across domains):
```python
"What's the weather like today?",
"Tell me a joke",
"Help me with my homework",
"Explain quantum physics",
"Write me a Python script",
"What's the capital of France?",
"Translate this to Spanish",
"Who won the Super Bowl?",
"Write a poem about love",
"What's the meaning of life?",
"Help me debug my React code",
"Explain the theory of relativity",
"What are the best Netflix shows?",
"Plan a vacation to Hawaii",
"How do I train for a marathon?",
```

Add 2-3 domain-adjacent off-topic phrases — things that SOUND related but are outside scope:
- Healthcare: "Can you diagnose my symptoms?", "Should I take this medication?"
- Finance: "Should I buy this stock?", "Give me crypto trading tips"
- Food delivery: "Give me a recipe for pasta", "How many calories are in a burger?"

**Distance thresholds:** On-topic = 0.7 (stricter, needs high similarity), Off-topic = 0.5 (looser, catches broader off-topic space).

### SeedMemory

At least 2 entries. These are preferences the demo user expressed in "previous conversations."

```python
SeedMemory(text="Prefers contactless delivery", topics=["delivery", "preferences"]),
SeedMemory(text="Likes spicy food", topics=["food", "preferences"]),
```

**Writing good seed memories:**
- Be specific and actionable — not "likes good food" but "Likes spicy food"
- Must be things the agent can use to personalize responses
- Must connect to demo paths — if demo step 4 says "Given what you know about me, recommend...", the memories must contain preferences that make that recommendation possible
- Use natural phrasing as if stored by an agent after a real conversation
- Topics should be 2-3 relevant tags for semantic retrieval

**Examples by vertical type:**
- Retail: "Prefers curbside pickup at Cherry Creek store", "Interested in gaming laptops and smart home devices"
- Healthcare: "Prefers morning appointments when available", "Primary care provider is Dr. Sofia Martinez at Downtown Medical"
- Banking: "Prefers paperless statements and online banking", "Interested in fixed deposit products for savings growth"
- Food delivery: "Prefers contactless delivery", "Likes spicy food"
- Finance: "Focuses on semiconductor sector — NVDA, AMD, AVGO are primary coverage", "Prefers quarterly earnings over annual filings for recent momentum analysis"

### SeedLangCacheEntry

At least 1 entry. This is a pre-cached Q&A pair. The prompt should match the "Cached" starter prompt card.

```python
SeedLangCacheEntry(
    prompt="What's your refund policy for late deliveries?",
    response="Our refund policy for late deliveries is based on how late the order arrives:\n\n- **15+ minutes late**: 20% credit on your next order\n- **30+ minutes late**: Full delivery fee refund\n- **45+ minutes late**: Full order refund\n\nCredits are applied automatically within 24 hours.",
    attributes={"domain": "<domain-id>"},
),
```

**Writing good cached responses:**
- Include specific numbers, percentages, timeframes — not vague generalities
- Use markdown **bold** for key facts
- Read like a real agent response: structured, concise, actionable
- The response should be 3-6 sentences — long enough to be useful, short enough to be scannable
- LangCache compares via vector similarity, so the prompt doesn't need to be an exact match with the starter card — but it should be semantically close

---

## System Prompt (`prompt.py`)

Every domain's `prompt.py` exports a `build_system_prompt(*, mcp_tools, memory_enabled=False)` function that returns the full system prompt string.

### Required structure

Follow the exact structure from `domains/reddash/prompt.py`:

```
1. Agent identity line (1 sentence)
2. ═══ AVAILABLE TOOLS ═══
   - Internal tools (always: identity, time, dataset_overview)
   - Memory tools (conditional on memory_enabled)
   - Context Surface tools (MCP tool hints)
3. ═══ CRITICAL RULES ═══
   - Rule about fetching fresh data
   - Rule about always calling tools
   - Rule about the `value` parameter (MANDATORY)
   - Domain-specific rules
   - Memory rules (conditional)
4. ═══ COMMON WORKFLOWS ═══
   - 3-5 numbered tool-call sequences for key scenarios
5. ═══ RESPONSE STYLE ═══
   - Tone and personality
   - Formatting rules (bold, no raw IDs, etc.)
   - Good/bad examples
```

### Tool discovery hints pattern

This pattern dynamically checks which MCP tools are available and includes hints only for those that exist. Copy the pattern from `domains/reddash/prompt.py` lines 7-24:

```python
tool_names = {tool.get("name", "") for tool in mcp_tools}
hints: list[str] = []
preferred = [
    ("filter_order_by_customer_id", "find all orders for a customer"),
    ("filter_orderitem_by_order_id", "get line items for an order"),
    ...
]
for name, description in preferred:
    if name in tool_names:
        hints.append(f"  * {name} -- {description}")
```

The `preferred` list should include all MCP tools the domain expects. Tool names follow the pattern: `filter_{entity}_by_{field}` and `search_{entity}_by_{field}`.

### The `value` parameter rule (MANDATORY)

This rule MUST appear in every prompt. Without it, the LLM passes field names as parameter keys (e.g., `patient_id="P001"` instead of `value="P001"`), which the MCP server rejects silently:

```
FOR FILTER TOOLS, pass plain entity IDs only — e.g. value="ORD_001",
value="CUST_DEMO_001". NEVER prepend Redis key prefixes like
"reddash_order:" or "reddash_customer:". The tool handles key resolution.
```

### Conditional memory block

The memory tools block and memory rules are only included when `memory_enabled=True`. Copy the pattern from `domains/reddash/prompt.py` lines 28-42. The memory block adds two tools: `search_customer_memory` and `remember_customer_detail`. The memory rules instruct the agent to use memory deliberately — pre-loaded context is already in the conversation, so `search_customer_memory` should only be called when the user explicitly asks about past preferences.

### Response style by vertical type

Adapt the tone to match the domain:
- **Food delivery** — warm, friendly, conversational (like DoorDash/Uber Eats support)
- **Healthcare** — empathetic, professional, reassuring (like a patient portal assistant)
- **Banking** — formal, trustworthy, precise (like a bank's customer service)
- **Retail** — enthusiastic, helpful, knowledgeable (like a store associate)
- **Finance** — analytical, data-driven, concise (like a Bloomberg terminal assistant)

All domains share these formatting rules:
- 2-3 sentences max for answers
- Use markdown **bold** for key facts (names, amounts, statuses, dates)
- Never expose internal IDs, UTC timestamps, or JSON field names
- When memory is used, naturally reference it: "Since you prefer **contactless delivery**..."

---

## Internal Tools

### Three mandatory tools

Every domain must register these in `get_internal_tool_definitions`:

1. **`get_current_user_profile`** — Returns identity from env vars. The `id_field` in the output dict must match `manifest.identity.id_field`. Implementation reads from env vars with fallback to defaults.

2. **`get_current_time`** — Returns current UTC timestamp in ISO 8601. Some domains hardcode a timestamp for demo consistency (reddash uses `2026-05-21T22:10:00+00:00`).

3. **`dataset_overview`** — Reads from Redis JSON at `manifest.namespace.dataset_meta_key` and returns entity counts. Implementation uses `redis.json().get(key)`.

### Optional domain-specific tools

Add tools for domain-specific actions the agent should perform. These are NOT for data retrieval (MCP tools handle that) — they're for state-changing operations.

Reference: `domains/radish-bank/domain.py` implements `place_fixed_deposit`, `buy_accident_insurance`, and `request_annual_card_fee_waiver`. Each tool:
- Has an `InternalToolDefinition` with `name`, `description`, and `input_schema` (JSON Schema)
- Is handled in `execute_internal_tool` with validation logic
- Reads/writes state (radish-bank appends to JSONL files in the output directory)

### Memory tools (conditional)

When `runtime_config["memory_enabled"]` is True, add:
- `search_customer_memory` — Searches long-term memory. Implemented in `aexecute_internal_tool` using `MemoryService`.
- `remember_customer_detail` — Stores a preference. Also async via `MemoryService`.

Copy the pattern from any existing domain's `aexecute_internal_tool` method.

---

## Data Generator (`data_generator.py`)

### Structure

```python
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "<domain-id>"
DEMO_USER_ID = "CUST_DEMO_001"  # Match manifest.identity.default_id
now = datetime.now(timezone.utc)  # All timestamps relative to now

# Embedding helper — falls back to fake embeddings when no OpenAI key
def embed(texts: list[str]) -> list[list[float]]: ...
def fake_embedding(text: str) -> list[float]: ...

# Data constants: CUSTOMERS, ORDERS, etc.
# Each is a list of dicts matching the entity schema

def generate_demo_data(*, output_dir: Path, seed: int | None = None, update_env_file: bool = False) -> GeneratedDataset:
    ...
```

### Critical rules

1. **`update_env_file` must default to `False`.** Only the `main()` guard passes `True`.
2. **DEMO_USER_ID must match `manifest.identity.default_id`.** The flagship demo user must be the first record in the primary user entity.
3. **Timestamps must be relative to `datetime.now(timezone.utc)`** so data is always "fresh."
4. **The embedding pattern** must check for `OPENAI_API_KEY` and fall back to `fake_embedding`. Copy from `domains/reddash/data_generator.py` lines 32-44.
5. **Write one JSONL file per entity** matching the `file_name` in the EntitySpec.
6. **Return `GeneratedDataset`** with `output_dir`, `env_updates` (dict of env var names to values), and `summary` (dict of entity names to record counts).

### Creating realistic demo data

The flagship demo user needs enough related records to support all demo paths. Create deliberate "interesting" scenarios:

- **Food delivery**: A late order (in_transit, past estimated_delivery), a completed order, a cancelled order, an active support ticket
- **Healthcare**: Upcoming appointment, completed appointment, pending referral, active waitlist entry
- **Banking**: Multiple accounts with different balances, an active card, product holdings, a pending service request
- **Retail**: Orders in different fulfillment states, a shipment with tracking events, a support case

Use realistic names, addresses, dollar amounts — not placeholder text. The demo is shown to customers and prospects.

### Env var updates

When `update_env_file=True`, the generator writes identity env vars to `.env`:
```python
env_updates = {
    "DEMO_USER_ID": DEMO_USER_ID,
    "DEMO_USER_NAME": "Alex Rivera",
    "DEMO_USER_EMAIL": "alex.rivera@example.com",
}
```

---

## Demo Paths (`docs/demo_paths.md`)

Write 2-4 scripted conversation paths. Each path should be a numbered sequence of user messages with annotations about what happens:

### Path structure

```markdown
## Path 1: [Scenario Name] (Context Retriever)

1. **User**: "Why is my order running late?"
   → Agent calls get_current_user_profile, filter_order_by_customer_id, get_current_time, filter_deliveryevent_by_order_id
   → Shows real-time order status with driver name and ETA

2. **User**: "Please remember that I prefer contactless delivery"
   → Agent calls remember_customer_detail
   → Confirms the preference was saved
```

### Required coverage

- **Path 1**: Flagship path exercising Context Retriever (MCP tools) — the most impressive multi-entity reasoning
- **Path 2**: Memory path — store a preference, then recall it in a follow-up question
- **Path 3** (optional): LangCache path — ask a question that matches a seed_langcache entry
- **Path 4** (optional): Edge case or complex multi-step scenario

Each path should reference specific record IDs and data from the generator.

---

## Frontend Assets

### Logo

Place at `domains/<domain-id>/assets/logo.svg` (SVG preferred, PNG/JPG/WebP also supported).

The backend reads this file and serves it as a base64 data URI. It renders at 28x28px in the topbar. Keep it simple and recognizable at small sizes.

### Landing page background SVGs

Place at `frontend/public/backgrounds/<domain-id>/`:
- `left.svg` (~590x817 pixels)
- `right.svg` (~632x817 pixels)

Requirements:
- Flat illustration style with domain-relevant objects
- Use the domain's accent color palette
- Objects fade toward the center (gradient opacity) to keep focus on the chat UI
- No text in the SVGs
- Under 35KB each

---

## Content Quality Philosophy

All text in the domain — prompts, guardrail routes, seed memories, demo data, starter prompts — must read as if written by or for a real customer of that vertical.

### What "realistic" means

**Think about what a real customer would actually say:**
- A DoorDash user says "Where's my food?" not "I'd like to inquire about the status of my delivery order"
- A bank customer says "What are my balances?" not "Please display my current account balance information"
- A healthcare patient says "Do I have any upcoming appointments?" not "Query my scheduled medical appointments"

**Think about what real business data looks like:**
- Restaurant names: "Sakura Sushi", "Bella Napoli", "Burger Barn" — not "Restaurant A", "Restaurant B"
- Product names: "MacBook Pro 16-inch M3 Max", "Sony WH-1000XM5" — not "Laptop 1", "Headphones 2"
- Doctor names: "Dr. Sofia Martinez", "Dr. James Chen" — not "Doctor 1", "Doctor 2"
- Dollar amounts: "$47.92", "SGD 1,000" — not "$100.00", "$50.00"

**Think about what real support scenarios look like:**
- A late food delivery with a specific reason (driver had a flat tire, restaurant was backed up)
- A healthcare referral stuck in "pending" status for 3 weeks
- A bank card with an annual fee waiver request that was recently approved
- An electronics order with a shipment that's been "in transit" for 5 days

### Adapting to new verticals

When creating a new vertical, research what real customers of that industry actually care about:
- **Telecom**: "Why is my bill so high?", "My internet keeps dropping", "How do I upgrade my plan?"
- **Travel**: "Can I change my flight?", "What's the cancellation policy?", "Where's my booking confirmation?"
- **Insurance**: "How do I file a claim?", "What does my policy cover?", "When does my premium renew?"
- **Education**: "When are office hours?", "How do I check my grades?", "Can I drop a course?"

The guardrail routes, starter prompts, seed memories, and demo data should all reflect these real concerns.

---

## Hyphenated Domain IDs

If the domain ID contains hyphens (e.g., `radish-bank`, `finance-researcher`), Python cannot use standard `from domains.radish-bank.schema import ...`. These domains must use `importlib` to load sub-modules. Reference `domains/radish-bank/domain.py` for the pattern:

```python
import importlib.util, sys
_dir = Path(__file__).resolve().parent
def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, _dir / fname)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
_schema = _load(f"domains.{DOMAIN_ID}.schema", "schema.py")
_prompt = _load(f"domains.{DOMAIN_ID}.prompt", "prompt.py")
```

Prefer simple, unhyphenated domain IDs when possible.

---

## Optional Advanced Features

### `get_runtime_config(settings)`

Returns a dict of runtime flags used by other methods. Common pattern:

```python
def get_runtime_config(self, settings) -> dict:
    return {"memory_enabled": bool(getattr(settings, "memory_api_base_url", None))}
```

### `build_answer_verifier_prompt(runtime_config)`

Returns a short instruction for the answer verifier that runs after the agent responds. Used to resolve follow-up references (e.g., "that order" → specific order ID).

### `describe_tool_trace_step(tool_name, payload, runtime_config)`

Returns human-readable descriptions for the activity trace panel. Maps tool names to explanation strings displayed in the UI.

### `UiConfig`

For domains with extra UI panels (e.g., finance-researcher's platform surface and live updates panels):

```python
ui=UiConfig(
    show_platform_surface=True,
    show_live_updates=True,
    platform_data_planes=["Context Surfaces", "RedisTimeSeries"],
)
```

---

## Validation Checklist

### `domain.py`
- [ ] `manifest.id` matches the folder name
- [ ] `generated_models_module` and `generated_models_path` match the folder
- [ ] `output_dir` is `output/<domain-id>`
- [ ] All namespace keys are unique (not shared with another domain)
- [ ] `logo_path` points to a real file under `domains/<domain-id>/assets/`
- [ ] `identity.default_id`, `default_name`, `default_email` match the first user in `data_generator.py`
- [ ] `identity.id_field` matches the domain's primary user ID field name
- [ ] `guardrail` has 20+ on-topic references and 15+ off-topic references
- [ ] `guardrail` on-topic references include conversational fillers (Yes, No, Sure, Thanks, Hello)
- [ ] `seed_memories` has 2+ entries with relevant topics
- [ ] `seed_langcache` has 1+ entry with a realistic prompt/response pair
- [ ] `seed_langcache[0].prompt` matches a "Cached" starter prompt card
- [ ] `branding.theme.landing_bg` is a hex color
- [ ] `branding.starter_prompts` has 4-5 entries (2 Context, 2 Memory, 1 Cached)
- [ ] `branding.demo_steps` has 4 entries

### `schema.py`
- [ ] Every entity has a unique `class_name`
- [ ] Every entity has a unique `file_name`
- [ ] Redis key templates use the domain namespace prefix
- [ ] Vector fields have `vector_dim=1536` and `distance_metric="cosine"`
- [ ] No `index="tag"` on fields with numeric `type_hint` (int/float)
- [ ] Exactly one entity has a vector embedding field (for RAG)
- [ ] `rag.index_name_contains` matches the RAG entity's class_name lowercased

### `prompt.py`
- [ ] Includes the `value` parameter hint for MCP filter/search tools
- [ ] Includes tool discovery hints using the `tool_names` set pattern
- [ ] Includes common workflows (3-5 tool-call sequences)
- [ ] Instructs agent to call `get_current_user_profile` first
- [ ] Memory block is conditional on `memory_enabled`
- [ ] Response style section includes good/bad examples

### `data_generator.py`
- [ ] `DEMO_USER_ID` matches `manifest.identity.default_id`
- [ ] Writes one JSONL file per entity matching schema `file_name`
- [ ] Returns `GeneratedDataset` with output_dir, env_updates, summary
- [ ] `update_env_file` defaults to `False`
- [ ] `main()` guard passes `update_env_file=True`
- [ ] Timestamps are relative to `datetime.now(timezone.utc)`
- [ ] Embedding helper falls back to `fake_embedding` when no OpenAI key
- [ ] Demo user has enough records to support all demo paths

### `docs/demo_paths.md`
- [ ] At least 2 paths
- [ ] Paths reference real data from the generator

### Frontend assets
- [ ] `domains/<domain-id>/assets/logo.<ext>` exists
- [ ] `frontend/public/backgrounds/<domain-id>/left.svg` exists
- [ ] `frontend/public/backgrounds/<domain-id>/right.svg` exists
- [ ] SVGs are under 35KB each

---

## Stop Conditions

Do NOT consider the domain complete if ANY of these remain:

- Placeholder prompts or entity specs
- Missing logo asset
- `validate_domain.py` fails
- `smoke_domain.py` fails
- `get_internal_tool_definitions` returns an empty tuple
- System prompt missing the `value` parameter hint
- `generate_demo_data` defaults `update_env_file=True` (must default False)
- Generated models use `Any` as relationship type annotations
- Missing guardrail routes (no `GuardrailConfig`)
- Missing seed memories (empty list)
- Missing seed langcache entries (empty list)
- Missing `landing_bg` in theme
- Missing landing page background SVGs
- Starter prompts reference data that doesn't exist in the generator
- Guardrail on-topic routes missing conversational fillers

---

## Validation Commands

```bash
# Validate domain contract
uv run python scripts/validate_domain.py --domain <domain-id>

# Generate typed models from schema
uv run python scripts/generate_models.py --domain <domain-id>

# Run smoke tests
uv run python scripts/smoke_domain.py --domain <domain-id>

# Full setup and test
make setup DOMAIN=<domain-id>
make dev
```
