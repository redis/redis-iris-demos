from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from backend.app.core.domain_contract import (
    BrandingConfig,
    DomainManifest,
    GeneratedDataset,
    GuardrailConfig,
    GuardrailRouteConfig,
    IdentityConfig,
    InternalToolDefinition,
    NamespaceConfig,
    PromptCard,
    RagConfig,
    SeedLangCacheEntry,
    SeedMemory,
    ThemeConfig,
)
from backend.app.core.domain_schema import EntitySpec, validate_entity_specs
from backend.app.memory_service import MemoryService
from backend.app.redis_connection import create_redis_client
from domains.crafthub.data_generator import DEMO_CUSTOMER, generate_demo_data
from domains.crafthub.prompt import build_system_prompt
from domains.crafthub.schema import ENTITY_SPECS

ROOT = Path(__file__).resolve().parents[2]

# Agent Memory scores natural recall questions ("Given what you know about me...")
# around 0.2-0.4 against the seeded preferences, so the global 0.7 default returns
# nothing. With only two seeded memories, a low threshold keeps recall reliable.
# MEMORY_SIMILARITY_THRESHOLD in .env still takes precedence.
DEFAULT_MEMORY_SIMILARITY_THRESHOLD = 0.2


class CrafthubDomain:
    manifest = DomainManifest(
        id="crafthub",
        description="Arts & crafts retail demo for project supplies, local store inventory, in-store classes, and order tracking.",
        generated_models_module="domains.crafthub.generated_models",
        generated_models_path="domains/crafthub/generated_models.py",
        output_dir="output/crafthub",
        branding=BrandingConfig(
            app_name="CraftHub",
            subtitle="Crafting",
            hero_title="What are you making today?",
            placeholder_text="Ask about project supplies, classes, pickup, or your order...",
            logo_path="domains/crafthub/assets/logo.svg",
            demo_steps=[
                "I want to make a fall wreath for my front door. What do I need, and is it in stock at my store?",
                "Please remember that I prefer curbside pickup at Las Colinas and I'm really into Cricut vinyl projects.",
                "Click Memory",
                "Given what you know about me, what should I check out next time I visit?",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Context",
                    title="Fall wreath supplies",
                    prompt="I want to make a fall wreath for my front door. What do I need, and is it in stock at my store?",
                ),
                PromptCard(
                    eyebrow="Context",
                    title="Track my Cricut order",
                    prompt="I haven't received my Cricut order yet.",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Save my crafting preferences",
                    prompt="Please remember that I teach 3rd grade and always need washable, kid-safe supplies.",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="What do you know about me?",
                    prompt="What are my crafting preferences and project interests?",
                ),
                PromptCard(
                    eyebrow="Cached",
                    title="Return policy",
                    prompt="What's your return policy?",
                ),
            ],
            theme=ThemeConfig(
                bg="#12100e",
                bg_accent_a="rgba(232, 102, 61, 0.14)",
                bg_accent_b="rgba(255, 209, 102, 0.08)",
                panel="rgba(26, 21, 18, 0.90)",
                panel_strong="rgba(31, 25, 21, 0.96)",
                panel_elevated="rgba(39, 31, 26, 0.94)",
                line="rgba(232, 102, 61, 0.12)",
                line_strong="rgba(232, 102, 61, 0.22)",
                text="#f7f2ec",
                muted="#a89a8c",
                soft="#e0d5c8",
                accent="#e8663d",
                user="#352519",
                landing_bg="#FFF6EE",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="crafthub",
            dataset_meta_key="crafthub:meta:dataset",
            checkpoint_prefix="crafthub:checkpoint",
            checkpoint_write_prefix="crafthub:checkpoint_write",
            redis_instance_name="CraftHub Redis Cloud",
            surface_name="CraftHub Commerce Surface",
            agent_name="CraftHub Maker's Assistant",
        ),
        rag=RagConfig(
            tool_name="vector_search_project_guides",
            status_text="Searching project guides and store policies…",
            generating_text="Generating answer…",
            index_name_contains="guide",
            vector_field="content_embedding",
            return_fields=["title", "category", "content"],
            num_results=3,
            answer_system_prompt=(
                "You are the CraftHub store associate assistant. Answer using only the provided guides and policies. "
                "If the guides do not contain the answer, say so plainly."
            ),
        ),
        identity=IdentityConfig(
            id_field="customer_id",
            default_id=DEMO_CUSTOMER["customer_id"],
            default_name=DEMO_CUSTOMER["name"],
            default_email=DEMO_CUSTOMER["email"],
            description=(
                "Returns the signed-in customer's profile, including CraftHub Rewards tier, points, and home store. "
                "Call this first for account, pickup, class, shipment, framing, or order-history questions."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="crafthub-guardrails",
            allowed_route_name="arts_and_crafts_retail",
            routes=[
                GuardrailRouteConfig(
                    name="arts_and_crafts_retail",
                    references=[
                        "I want to make a fall wreath",
                        "What do I need for a DIY project?",
                        "Do you have Cricut vinyl in stock?",
                        "Which Cricut machine should I buy?",
                        "I'm looking for chunky blanket yarn",
                        "What yarn should I use for a baby blanket?",
                        "Do you carry acrylic paint and canvases?",
                        "What's on sale this week?",
                        "Is this in stock at my store?",
                        "Can I pick that up curbside?",
                        "Are there any classes this weekend?",
                        "Do you have kids' crafts classes?",
                        "Sign me up for a knitting class",
                        "When will my custom frame be ready?",
                        "How much does custom framing cost?",
                        "I haven't received my order yet",
                        "Where is my package?",
                        "Track my order",
                        "Show me my recent orders",
                        "What's your return policy?",
                        "Can I return a Cricut machine?",
                        "How many Rewards points do I have?",
                        "Do you have Halloween decorations?",
                        "I need supplies for my classroom",
                        "What stores are near me?",
                        "What are your store hours?",
                        "Remember that I like knitting",
                        "What do you know about me?",
                        "Yes",
                        "No",
                        "Sure",
                        "Thanks",
                        "Tell me more",
                        "Go ahead",
                        "Hello",
                        "Hi there",
                        "Can you help me?",
                        "That's all, thanks",
                        "Yes please",
                        "What else can you help with?",
                    ],
                    distance_threshold=0.7,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "What's the weather like today?",
                        "Tell me a joke",
                        "Write me a Python script",
                        "Help me with my homework",
                        "Who won the Super Bowl?",
                        "Explain quantum physics",
                        "What's the latest news?",
                        "Translate this to Spanish",
                        "What's the capital of France?",
                        "Give me a recipe for pumpkin pie",
                        "What's the stock market doing?",
                        "Who is the president?",
                        "Solve this math equation",
                        "Plan a vacation to Hawaii",
                        "What are the best Netflix shows?",
                        "Can you fix my car?",
                        "Recommend a good laptop to buy",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(
                text="Crafting interests: knits chunky blankets and is getting into Cricut vinyl projects",
                topics=["crafts", "interests", "preferences"],
            ),
            SeedMemory(
                text="Shopping preference: prefers curbside pickup at the CraftHub Las Colinas store",
                topics=["shopping", "pickup", "preferences"],
            ),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="What's your return policy?",
                response=(
                    "Most unused items in original condition can be returned within **60 days** with a receipt, in store or by mail. "
                    "**Cricut machines and electronics** have a **30-day** window and need their original packaging. "
                    "**Custom framing, cut fabric, and personalized items are final sale.** "
                    "Without a receipt, returns are refunded as **store credit** at the lowest recent selling price."
                ),
                attributes={"domain": "crafthub"},
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def get_runtime_config(self, *, settings: Any) -> dict[str, Any]:
        memory_enabled = MemoryService(settings).is_configured() if settings else False
        return {
            "memory_enabled": memory_enabled,
            "memory_similarity_threshold": DEFAULT_MEMORY_SIMILARITY_THRESHOLD,
        }

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        return build_system_prompt(
            mcp_tools=mcp_tools,
            memory_enabled=bool((runtime_config or {}).get("memory_enabled")),
        )

    def build_answer_verifier_prompt(self, *, runtime_config: dict[str, Any] | None = None) -> str:
        return ""

    def describe_tool_trace_step(
        self,
        *,
        tool_name: str,
        payload: Any,
        runtime_config: dict[str, Any] | None = None,
    ) -> str | None:
        detail = ""
        if isinstance(payload, dict):
            for key in ("query", "text", "product_id", "store_id", "order_id", "shipment_id", "customer_id"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in maker, Rewards tier, and home store before using live data."
        if tool_name == "get_current_time":
            return "Compare live timestamps against promise dates, framing-ready dates, and class times."
        if tool_name.startswith("search_product_by_text"):
            return f"Search the craft catalog for project supplies: {detail or 'product search'}."
        if tool_name.startswith("filter_storeinventory"):
            return "Verify live store inventory and pickup timing before promising availability."
        if tool_name.startswith(("filter_workshop", "search_workshop")):
            return "Check in-store class schedules and open seats."
        if tool_name.startswith("search_guide_by_text"):
            return f"Pull a project guide or store policy: {detail or 'guide search'}."
        if tool_name == "search_customer_memory":
            return "Search durable customer memory for craft interests and preferences."
        if tool_name == "remember_customer_detail":
            return "Store a durable customer preference for future conversations."
        return None

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        definitions: list[InternalToolDefinition] = [
            InternalToolDefinition(
                name=self.manifest.identity.tool_name,
                description=self.manifest.identity.description,
            ),
            InternalToolDefinition(
                name="get_current_time",
                description=(
                    "Returns the current date and time in UTC (ISO 8601). Use this when comparing order promises, "
                    "shipment scans, custom framing ready dates, and class times."
                ),
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description=(
                    "Returns counts for the current CraftHub demo dataset, including customers, stores, products, "
                    "inventory rows, classes, orders, shipments, cases, and guides."
                ),
            ),
        ]
        if (runtime_config or {}).get("memory_enabled"):
            definitions.extend(
                [
                    InternalToolDefinition(
                        name="search_customer_memory",
                        description=(
                            "Search durable customer memory for craft interests, preferences, or facts from previous sessions. "
                            "Use this when the user asks what you remember, refers to preferences, or wants continuity across conversations."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "What to look up in customer memory."},
                                "limit": {"type": "integer", "description": "Optional max number of memories to return.", "default": 5},
                            },
                            "required": ["query"],
                        },
                    ),
                    InternalToolDefinition(
                        name="remember_customer_detail",
                        description=(
                            "Save a durable customer preference or fact into long-term memory. "
                            "Only use this when the user explicitly asks you to remember something or states a lasting preference."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "The exact customer preference or durable fact to remember."},
                                "memory_type": {
                                    "type": "string",
                                    "description": "Memory type: semantic for preferences/facts, episodic for a notable event, message for a verbatim note.",
                                    "default": "semantic",
                                },
                                "topics": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional topic tags like crafts, pickup, classes, preferences.",
                                },
                            },
                            "required": ["text"],
                        },
                    ),
                ]
            )
        return tuple(definitions)

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            return {
                identity.id_field: os.getenv(identity.id_env_var, identity.default_id),
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
                "member_tier": os.getenv("DEMO_USER_MEMBER_TIER", DEMO_CUSTOMER["member_tier"]),
                "rewards_points": DEMO_CUSTOMER["rewards_points"],
                "city": os.getenv("DEMO_USER_CITY", DEMO_CUSTOMER["city"]),
                "state": os.getenv("DEMO_USER_STATE", DEMO_CUSTOMER["state"]),
                "home_store_id": os.getenv("DEMO_USER_HOME_STORE_ID", DEMO_CUSTOMER["home_store_id"]),
                "home_store_name": os.getenv("DEMO_USER_HOME_STORE_NAME", DEMO_CUSTOMER["home_store_name"]),
            }
        if tool_name == "get_current_time":
            return {
                "current_time": datetime.now(timezone.utc).isoformat(),
                "timezone": "UTC",
            }
        if tool_name == "dataset_overview":
            client = create_redis_client(settings)
            raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
            if raw:
                data = json.loads(raw)
                return data[0] if isinstance(data, list) else data
            return {"error": "Dataset metadata not found. Run the data loader first."}
        return {"error": f"Unknown tool: {tool_name}"}

    async def aexecute_internal_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        settings: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if tool_name not in {"search_customer_memory", "remember_customer_detail"}:
            return self.execute_internal_tool(tool_name, arguments, settings)

        identity = self.manifest.identity
        owner_id = os.getenv(identity.id_env_var, identity.default_id)
        memory_service = MemoryService(
            settings,
            similarity_threshold=(runtime_config or {}).get("memory_similarity_threshold"),
        )
        if not memory_service.is_configured():
            return {"error": "Memory service is not configured for this demo."}

        if tool_name == "search_customer_memory":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return {"error": "query is required"}
            limit = arguments.get("limit")
            memories = await memory_service.asearch_long_term_memory(
                text=query,
                owner_id=owner_id,
                limit=int(limit) if limit is not None else None,
            )
            return {
                "owner_id": owner_id,
                "query": query,
                "memory_count": len(memories),
                "memories": [
                    {
                        "id": memory.get("id"),
                        "text": memory.get("text"),
                        "memory_type": memory.get("memoryType"),
                        "topics": memory.get("topics", []),
                        "session_id": memory.get("sessionId"),
                        "created_at": memory.get("createdAt"),
                    }
                    for memory in memories
                ],
            }

        # remember_customer_detail — blocked in demo mode
        text = str(arguments.get("text", "")).strip()
        if not text:
            return {"error": "text is required"}
        memory_type = str(arguments.get("memory_type", "semantic")).strip() or "semantic"
        if memory_type not in {"semantic", "episodic", "message"}:
            memory_type = "semantic"
        topics = arguments.get("topics") or []
        if not isinstance(topics, list):
            topics = []
        return {
            "owner_id": owner_id,
            "saved_text": text,
            "memory_type": memory_type,
            "topics": [str(t).strip() for t in topics if str(t).strip()],
            "demo_blocked": True,
            "response": {"acknowledged": True},
        }

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        summary = {
            "customers": len(records.get("Customer", [])),
            "stores": len(records.get("Store", [])),
            "products": len(records.get("Product", [])),
            "store_inventory": len(records.get("StoreInventory", [])),
            "workshops": len(records.get("Workshop", [])),
            "orders": len(records.get("Order", [])),
            "order_items": len(records.get("OrderItem", [])),
            "shipments": len(records.get("Shipment", [])),
            "shipment_events": len(records.get("ShipmentEvent", [])),
            "support_cases": len(records.get("SupportCase", [])),
            "guides": len(records.get("Guide", [])),
        }
        client = create_redis_client(settings)
        client.execute_command(
            "JSON.SET",
            self.manifest.namespace.dataset_meta_key,
            "$",
            json.dumps(summary, ensure_ascii=False),
        )
        return summary

    def generate_demo_data(
        self,
        *,
        output_dir: Path,
        seed: int | None = None,
        update_env_file: bool = False,
    ) -> GeneratedDataset:
        return generate_demo_data(output_dir=output_dir, seed=seed, update_env_file=update_env_file)

    def validate(self) -> list[str]:
        errors = validate_entity_specs(self.get_entity_specs())
        if not (ROOT / self.manifest.branding.logo_path).exists():
            errors.append(f"Logo file not found: {self.manifest.branding.logo_path}")
        if not self.manifest.branding.starter_prompts:
            errors.append("Branding must define at least one starter prompt")
        return errors


DOMAIN = CrafthubDomain()
