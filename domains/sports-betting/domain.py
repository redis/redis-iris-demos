from __future__ import annotations

import importlib.util
import json
import os
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

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_DIR = Path(__file__).resolve().parent
DEMO_CURRENT_TIME = "2026-05-21T22:10:00+00:00"


def _load_local_module(module_name: str, file_name: str):
    module_path = DOMAIN_DIR / file_name
    spec = importlib.util.spec_from_file_location(f"sports_betting_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load sports-betting module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")

generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS
DEMO_PLAYER_ID = _data_generator.DEMO_PLAYER_ID


class SportsBettingDomain:
    manifest = DomainManifest(
        id="sports-betting",
        description=(
            "Sportsbook support demo showing Context Retriever, "
            "LangCache, and Agent Memory across betting, settlement, wallet, and "
            "safer-gambling workflows."
        ),
        generated_models_module="domains.sports-betting.generated_models",
        generated_models_path="domains/sports-betting/generated_models.py",
        output_dir="output/sports-betting",
        branding=BrandingConfig(
            app_name="Sports Desk",
            subtitle="Sportsbook Support",
            hero_title="How can we help?",
            placeholder_text="Ask about bets, settlement, cash out, wallet activity, or safer-gambling...",
            logo_path="domains/sports-betting/assets/logo.svg",
            demo_steps=[
                "Why has my football bet not settled yet?",
                "Please remember that I prefer football accumulators and keep stakes under GBP 25.",
                "Click Memory",
                "Given what you know about me, review my recent bets and tell me whether the open slip fits my preferences.",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Context",
                    title="Delayed settlement",
                    prompt="Why has my football bet not settled yet?",
                ),
                PromptCard(
                    eyebrow="Context",
                    title="Wallet activity",
                    prompt="Show me my recent wallet activity and whether that bet has paid out",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Save stake preference",
                    prompt="Please remember that I prefer football accumulators and keep stakes under GBP 25",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Personalized review",
                    prompt="Given what you know about me, review my recent bets and tell me whether the open slip fits my preferences",
                ),
                PromptCard(
                    eyebrow="Cached",
                    title="Settlement timing",
                    prompt="How long does bet settlement usually take?",
                ),
            ],
            theme=ThemeConfig(
                bg="#08120f",
                bg_accent_a="rgba(0, 199, 140, 0.12)",
                bg_accent_b="rgba(248, 210, 76, 0.10)",
                panel="rgba(12, 25, 22, 0.9)",
                panel_strong="rgba(14, 31, 27, 0.97)",
                panel_elevated="rgba(20, 41, 36, 0.94)",
                line="rgba(0, 199, 140, 0.16)",
                line_strong="rgba(248, 210, 76, 0.24)",
                text="#eff8f3",
                muted="#91ada2",
                soft="#d5eadf",
                accent="#00c78c",
                user="#11251f",
                landing_bg="#EEF8F2",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="sports-betting",
            dataset_meta_key="sports-betting:meta:dataset",
            checkpoint_prefix="sports-betting:checkpoint",
            checkpoint_write_prefix="sports-betting:checkpoint_write",
            redis_instance_name="Sports Desk Redis Cloud",
            surface_name="Sportsbook Context Surface",
            agent_name="Sports Desk Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_sportsbook_policies",
            status_text="Searching sportsbook policies via vector similarity...",
            generating_text="Generating answer...",
            index_name_contains="policy",
            vector_field="content_embedding",
            return_fields=["title", "category", "content", "policy_id"],
            num_results=3,
            answer_system_prompt=(
                "You are the Sports Desk policy assistant. Answer using only "
                "the sportsbook policy documents below. If the retrieved policies do "
                "not cover the question, say so briefly. Keep safer-gambling guidance "
                "supportive and do not encourage additional betting."
            ),
        ),
        identity=IdentityConfig(
            default_id=DEMO_PLAYER_ID,
            default_name="Maya Shah",
            default_email="maya.shah@example.com",
            id_field="player_id",
            description=(
                "Returns the signed-in sportsbook player's ID, name, and email. "
                "Call this whenever the user asks about bets, wallet activity, support tickets, account status, "
                "or safer-gambling settings."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="sports-betting-guardrails",
            allowed_route_name="sportsbook_support",
            routes=[
                GuardrailRouteConfig(
                    name="sportsbook_support",
                    references=[
                        "Why has my bet not settled?",
                        "Has my accumulator paid out yet?",
                        "Show me my recent bets",
                        "What happened with my football slip?",
                        "Is cash out available?",
                        "Why was cash out suspended?",
                        "Show me my wallet transactions",
                        "Did I receive my payout?",
                        "What are the settlement rules?",
                        "How long does settlement take?",
                        "Explain my responsible gambling limits",
                        "Remember my stake limit preference",
                        "What do you remember about my betting preferences?",
                        "I need help with a sportsbook support ticket",
                        "Can you help me understand a void bet?",
                    ],
                    distance_threshold=0.7,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "Write me a Python script",
                        "What is the weather tomorrow?",
                        "Tell me a joke",
                        "Who won the election?",
                        "Help me with my homework",
                        "Generate an image of a spaceship",
                        "What is the capital of France?",
                        "Explain quantum physics",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(
                text="Prefers football accumulators with stakes under GBP 25",
                topics=["football", "accumulator", "stake_preferences"],
            ),
            SeedMemory(
                text="Wants safer-gambling reminders before changing deposit limits",
                topics=["responsible_gaming", "limits", "preferences"],
            ),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="How long does bet settlement usually take?",
                response=(
                    "Most sportsbook bets settle within a few minutes of official result confirmation. "
                    "Accumulators settle only after every leg has a verified result, and any leg in trading "
                    "review can hold the whole bet until verification completes. If official data changes or "
                    "an integrity check is active, settlement may take longer."
                ),
                attributes={"domain": "sports-betting", "topic": "settlement"},
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
            "When the user refers to 'that bet', 'that payout', 'the accumulator', or similar follow-ups, resolve "
            "the reference to the exact bet, wallet transaction, settlement event, or support ticket from the prior turn. "
            "Do not mention payout eligibility, settlement timing, cash out, or safer-gambling outcomes unless the tool "
            "results or cited policy support them."
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
            for key in ("query", "text", "bet_id", "player_id", "ticket_id", "transaction_id", "event_id", "market_id"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in player before checking account, bet, or wallet data."
        if tool_name == "get_current_time":
            return "Compare the current time against event and settlement timestamps."
        if tool_name.startswith("search_policy_by_text"):
            return f"Search sportsbook policy guidance: {detail or 'policy search'}."
        if tool_name.startswith("filter_bet_by_"):
            return "Inspect the player's live bet records before answering."
        if tool_name.startswith("filter_betleg_by_"):
            return "Check the bet legs and selection outcomes for the relevant slip."
        if tool_name.startswith("filter_betsettlementevent_by_"):
            return "Review the settlement timeline for the bet."
        if tool_name.startswith("filter_wallettransaction_by_"):
            return "Inspect wallet movement before answering payout, stake, or refund questions."
        if tool_name == "search_customer_memory":
            return "Search durable player memory for preferences, limits, or support continuity."
        if tool_name == "remember_customer_detail":
            return "Store a durable player preference or safer-gambling commitment for future conversations."
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
                    "Use this to compare event start times, settlement windows, and wallet timing."
                ),
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description=(
                    "Returns a summary of the current sports-betting dataset: counts of players, events, "
                    "markets, bets, wallet transactions, support tickets, and policies."
                ),
            ),
        ]
        if (runtime_config or {}).get("memory_enabled"):
            tools.extend(
                [
                    InternalToolDefinition(
                        name="search_customer_memory",
                        description=(
                            "Search durable player memory for preferences, responsible-gaming commitments, "
                            "or support continuity from previous sessions."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "What to look up in player memory."},
                                "limit": {"type": "integer", "description": "Optional max number of memories to return.", "default": 5},
                            },
                            "required": ["query"],
                        },
                    ),
                    InternalToolDefinition(
                        name="remember_customer_detail",
                        description=(
                            "Save a durable player preference, safer-gambling commitment, or support fact into long-term memory. "
                            "Only use this when the user explicitly asks you to remember something or states a lasting preference."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "The exact player preference or durable fact to remember."},
                                "memory_type": {
                                    "type": "string",
                                    "description": "Memory type: semantic for preferences/facts, episodic for a notable event, message for a verbatim note.",
                                    "default": "semantic",
                                },
                                "topics": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional topic tags like football, stake_preferences, settlement, limits.",
                                },
                            },
                            "required": ["text"],
                        },
                    ),
                ]
            )
        return tuple(tools)

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            return {
                identity.id_field: os.getenv(identity.id_env_var, identity.default_id),
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
            }
        if tool_name == "get_current_time":
            return {"current_time": DEMO_CURRENT_TIME, "timezone": "UTC"}
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
            "players": len(records.get("Player", [])),
            "sport_events": len(records.get("SportEvent", [])),
            "markets": len(records.get("Market", [])),
            "bets": len(records.get("Bet", [])),
            "bet_legs": len(records.get("BetLeg", [])),
            "bet_settlement_events": len(records.get("BetSettlementEvent", [])),
            "wallet_transactions": len(records.get("WalletTransaction", [])),
            "support_tickets": len(records.get("SupportTicket", [])),
            "policies": len(records.get("Policy", [])),
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
        background_dir = ROOT / "frontend" / "public" / "backgrounds" / self.manifest.id
        for filename in ("left.svg", "right.svg"):
            if not (background_dir / filename).exists():
                errors.append(f"Landing background file not found: frontend/public/backgrounds/{self.manifest.id}/{filename}")
        return errors


DOMAIN = SportsBettingDomain()
