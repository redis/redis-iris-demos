from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Sequence

from backend.app.memory_service import MemoryService
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
from backend.app.redis_connection import create_redis_client
from domains.rmobile.data_generator import generate_demo_data
from domains.rmobile.prompt import build_system_prompt
from domains.rmobile.schema import ENTITY_SPECS

ROOT = Path(__file__).resolve().parents[2]


class RMobileDomain:
    manifest = DomainManifest(
        id="rmobile",
        description="Wireless carrier account-support demo for R-Mobile, modeled after T-Mobile / AT&T / Verizon.",
        generated_models_module="domains.rmobile.generated_models",
        generated_models_path="domains/rmobile/generated_models.py",
        output_dir="output/rmobile",
        branding=BrandingConfig(
            app_name="R-Mobile",
            subtitle="Account Support",
            hero_title="How can we help you today?",
            placeholder_text="Ask about your bill, plans, devices, or coverage...",
            logo_path="domains/rmobile/assets/logo.svg",
            demo_steps=[
                "Why is my bill higher than last month?",
                "I always want paperless billing and autopay on",
                "Click Memory",
                "How can I lower my monthly bill?",
            ],
            starter_prompts=[
                PromptCard(eyebrow="Context", title="Why is my bill so high?", prompt="Why is my bill higher than last month?"),
                PromptCard(eyebrow="Context", title="Device upgrade eligibility", prompt="Am I eligible to upgrade my phone?"),
                PromptCard(eyebrow="Memory", title="Save preferences", prompt="I always want paperless billing and autopay on"),
                PromptCard(eyebrow="Memory", title="Bill advice", prompt="How can I lower my monthly bill?"),
                PromptCard(eyebrow="Cached", title="Trade-in policy", prompt="What is your device trade-in policy?"),
            ],
            theme=ThemeConfig(
                bg="#0d0a12",
                bg_accent_a="rgba(226, 0, 116, 0.12)",
                bg_accent_b="rgba(180, 0, 90, 0.08)",
                panel="rgba(18, 14, 24, 0.90)",
                panel_strong="rgba(22, 16, 32, 0.96)",
                panel_elevated="rgba(28, 20, 40, 0.92)",
                line="rgba(226, 0, 116, 0.10)",
                line_strong="rgba(226, 0, 116, 0.20)",
                text="#f2eef5",
                muted="#9a8fa3",
                soft="#d4ccdb",
                accent="#e20074",
                user="#1e1428",
                landing_bg="#F5F5F5",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="rmobile",
            dataset_meta_key="rmobile:meta:dataset",
            checkpoint_prefix="rmobile:checkpoint",
            checkpoint_write_prefix="rmobile:checkpoint_write",
            redis_instance_name="R-Mobile Redis Cloud",
            surface_name="R-Mobile Account Surface",
            agent_name="R-Mobile Support Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_policy_docs",
            status_text="Searching R-Mobile policy documents…",
            generating_text="Generating answer from policies…",
            index_name_contains="policydoc",
            vector_field="content_embedding",
            return_fields=["title", "category", "content", "doc_id"],
            num_results=3,
            answer_system_prompt=(
                "You are R-Mobile's policy and account-support assistant. "
                "Answer using only the retrieved policy documents. If they do not cover "
                "the question, say so briefly. Be concise and helpful."
            ),
        ),
        identity=IdentityConfig(
            default_id="CUST_DEMO_001",
            default_name="Jamie Torres",
            default_email="jamie.torres@example.com",
            description=(
                "Returns the signed-in customer's ID, name, and email. "
                "Call this whenever the user asks about their account, bills, lines, or devices."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="rmobile-guardrails",
            allowed_route_name="wireless_support",
            routes=[
                GuardrailRouteConfig(
                    name="wireless_support",
                    references=[
                        "Why is my bill so high this month?",
                        "What's this charge on my bill?",
                        "Set up autopay",
                        "I need a payment extension",
                        "I want to dispute a charge",
                        "How do I upgrade my phone?",
                        "I want to trade in my phone",
                        "Do I have device insurance?",
                        "How do I unlock my phone?",
                        "What plans do you offer?",
                        "I want to change my plan",
                        "I want to add someone to my plan",
                        "How much data have I used?",
                        "Do you have international plans?",
                        "How much is roaming in Mexico?",
                        "I have no signal at home",
                        "Is there an outage in my area?",
                        "My calls keep dropping",
                        "Update my billing address",
                        "I want to cancel my service",
                        "Remember that I travel internationally often",
                        "What do you know about my preferences?",
                        "Yes",
                        "No thanks",
                        "Sure",
                        "Thanks",
                        "Hello",
                        "OK",
                    ],
                    distance_threshold=0.7,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "What's the weather like today?",
                        "Write me a Python script",
                        "Help me with my homework",
                        "Tell me a joke",
                        "Who won the Super Bowl?",
                        "Explain quantum physics",
                        "Write a poem about love",
                        "Who is the president?",
                        "Translate this to Spanish",
                        "Help me debug my code",
                        "What's the meaning of life?",
                        "Can you help me fix my WiFi router?",
                        "Compare T-Mobile vs Verizon for me",
                        "What phone should I buy from Best Buy?",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(text="Prefers to manage everything through the app", topics=["account", "preferences"]),
            SeedMemory(text="Likes to keep monthly bill under $160", topics=["billing", "preferences"]),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="What is your device trade-in policy?",
                response=(
                    "Our trade-in program lets you trade in your current device toward a new one. "
                    "Here's how it works:\n\n"
                    "- **Eligible devices** are assessed based on condition — screen, buttons, and power must all be functional\n"
                    "- **Trade-in value** is applied as **monthly bill credits over 24 months**, not a one-time discount\n"
                    "- **If you cancel** your line before 24 months, the remaining credits are forfeited\n"
                    "- **Mail-in or in-store**: You have 30 days after activation to return your trade-in device\n\n"
                    "For example, a recent iPhone in good condition can qualify for up to **$800 in credits** "
                    "toward a new device. Want me to check what your current device is worth?"
                ),
                attributes={"domain": "rmobile"},
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def get_runtime_config(self, settings: Any) -> dict[str, Any]:
        memory_enabled = MemoryService(settings).is_configured() if settings else False
        return {
            "memory_enabled": memory_enabled,
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
        del runtime_config
        return (
            "When the user refers to 'that charge', 'that line', 'my bill', or similar follow-ups, resolve the reference to the exact "
            "bill, charge, line, or device from the prior turn. Do not mention credits, refunds, or policy outcomes unless the "
            "tool results or cited policy support them."
        )

    def describe_tool_trace_step(
        self,
        *,
        tool_name: str,
        payload: Any,
        runtime_config: dict[str, Any] | None = None,
    ) -> str | None:
        del runtime_config
        detail = ""
        if isinstance(payload, dict):
            for key in ("query", "text", "customer_id", "bill_id", "line_id", "device_id", "ticket_id"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in customer before checking account data."
        if tool_name == "get_current_time":
            return "Compare the current time against bill due dates and device eligibility."
        if tool_name.startswith("search_policydoc"):
            return f"Search R-Mobile policy guidance: {detail or 'policy search'}."
        if tool_name.startswith("filter_bill"):
            return "Look up billing history and charges for the account."
        if tool_name.startswith("filter_billcharge"):
            return "Inspect the line-item charges on a bill."
        if tool_name.startswith("filter_line"):
            return "Check the phone lines, plans, and usage on the account."
        if tool_name.startswith("filter_device"):
            return "Check device details, installment balances, and upgrade eligibility."
        if tool_name.startswith("filter_supportticket"):
            return "Review past support tickets for the account."
        if tool_name.startswith("search_plan") or tool_name.startswith("filter_plan"):
            return "Look up available wireless plans."
        if tool_name == "search_customer_memory":
            return "Search durable customer memory for preferences, past issues, or stored context."
        if tool_name == "remember_customer_detail":
            return "Store a durable customer fact or preference for future conversations."
        return None

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        tools: list[InternalToolDefinition] = [
            InternalToolDefinition(
                name=self.manifest.identity.tool_name,
                description=self.manifest.identity.description,
            ),
            InternalToolDefinition(
                name="get_current_time",
                description=(
                    "Returns the current date and time in UTC (ISO 8601). "
                    "Use this to compare against bill due dates, device upgrade eligibility, and ticket timestamps."
                ),
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description="Returns a summary of the current R-Mobile dataset: counts of customers, lines, plans, devices, bills, and policies.",
            ),
        ]
        if (runtime_config or {}).get("memory_enabled"):
            tools.extend(
                [
                    InternalToolDefinition(
                        name="search_customer_memory",
                        description=(
                            "Search durable customer memory for preferences, prior incidents, or facts from previous sessions. "
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
                                    "description": "Optional topic tags like billing, plans, devices, international.",
                                },
                            },
                            "required": ["text"],
                        },
                    ),
                ]
            )
        return tuple(tools)

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        from datetime import datetime, timezone

        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            return {
                identity.id_field: os.getenv(identity.id_env_var, identity.default_id),
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
            }
        if tool_name == "get_current_time":
            return {"current_time": datetime.now(timezone.utc).isoformat(), "timezone": "UTC"}
        if tool_name == "dataset_overview":
            client = create_redis_client(settings)
            raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
            if raw:
                data = json.loads(raw)
                return data[0] if isinstance(data, list) else data
            return {"error": "Dataset metadata not found. Run the data loader first."}
        return {"error": f"Unknown tool: {tool_name}"}

    async def aexecute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name not in {"search_customer_memory", "remember_customer_detail"}:
            return self.execute_internal_tool(tool_name, arguments, settings)

        identity = self.manifest.identity
        owner_id = os.getenv(identity.id_env_var, identity.default_id)
        memory_service = MemoryService(settings)
        if not memory_service.is_configured():
            return {"error": "Memory service is not configured for this demo."}

        if tool_name == "search_customer_memory":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return {"error": "query is required"}
            limit = arguments.get("limit")
            try:
                memories = await memory_service.asearch_long_term_memory(
                    text=query,
                    owner_id=owner_id,
                    limit=int(limit) if limit is not None else None,
                )
            except Exception as exc:
                return {"error": f"Memory search unavailable: {exc}", "memories": [], "memory_count": 0}
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
            "lines": len(records.get("Line", [])),
            "plans": len(records.get("Plan", [])),
            "devices": len(records.get("Device", [])),
            "bills": len(records.get("Bill", [])),
            "bill_charges": len(records.get("BillCharge", [])),
            "support_tickets": len(records.get("SupportTicket", [])),
            "policy_docs": len(records.get("PolicyDoc", [])),
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
        update_env_file: bool = True,
    ) -> GeneratedDataset:
        return generate_demo_data(output_dir=output_dir, seed=seed, update_env_file=update_env_file)

    def validate(self) -> list[str]:
        errors = validate_entity_specs(self.get_entity_specs())
        if not (ROOT / self.manifest.branding.logo_path).exists():
            errors.append(f"Logo file not found: {self.manifest.branding.logo_path}")
        if not self.manifest.branding.starter_prompts:
            errors.append("Branding must define at least one starter prompt")
        return errors


DOMAIN = RMobileDomain()
