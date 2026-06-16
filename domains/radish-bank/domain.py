from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
from datetime import datetime, timedelta, timezone
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


def _load_local_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(f"radish_bank_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load radish-bank module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")

generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS
DEMO_CUSTOMER_ID = _data_generator.DEMO_CUSTOMER_ID

OUTPUT_DIR = ROOT / "output" / "radish-bank"


def _load_generated_models():
    path = ROOT / "domains" / "radish-bank" / "generated_models.py"
    spec = importlib.util.spec_from_file_location("radish_bank_generated_models", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Missing generated models at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _next_id(prefix: str, rows: list[dict[str, Any]], key: str) -> str:
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    best = 0
    for row in rows:
        m = pat.match(str(row.get(key, "")))
        if m:
            best = max(best, int(m.group(1)))
    return f"{prefix}{best + 1:03d}"


async def _import_records(settings: Any, records: list[Any]) -> dict[str, Any]:
    from context_surfaces import UnifiedClient

    if not settings.ctx_admin_key or not settings.ctx_surface_id:
        return {"error": "CTX_ADMIN_KEY and CTX_SURFACE_ID must be set to persist mutations."}
    async with UnifiedClient() as client:
        result = await client.import_data(
            admin_key=settings.ctx_admin_key,
            context_surface_id=settings.ctx_surface_id,
            records=records,
            on_conflict="overwrite",
            on_error="fail_fast",
        )
        return {
            "imported": result.imported,
            "failed": result.failed,
            "errors": [str(e) for e in (result.errors or [])],
        }


def _run_import(settings: Any, records: list[Any]) -> dict[str, Any]:
    return asyncio.run(_import_records(settings, records))


class RadishBankDomain:
    manifest = DomainManifest(
        id="radish-bank",
        description="Radish Bank retail demo: structured accounts plus policy docs and three service actions.",
        generated_models_module="domains.radish-bank.generated_models",
        generated_models_path="domains/radish-bank/generated_models.py",
        output_dir="output/radish-bank",
        branding=BrandingConfig(
            app_name="Radish Bank",
            subtitle="Customer Care",
            hero_title="Banking Made Easy",
            placeholder_text="Ask about accounts, cards, FDs, insurance, branches, or fee waivers…",
            logo_path="domains/radish-bank/assets/logo.svg",
            demo_steps=[
                "What are my current account balances?",
                "Please remember that I prefer paperless statements and am interested in fixed deposits.",
                "Click Memory",
                "Given what you know about my preferences, what banking products would you recommend for me?",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Context",
                    title="What are my account balances?",
                    prompt="What accounts do I have and what are my current balances?",
                ),
                PromptCard(
                    eyebrow="Context",
                    title="Recent service requests",
                    prompt="Show me my recent service requests",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Save banking preferences",
                    prompt="Please remember that I prefer mobile banking and contactless payments",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Product recommendations",
                    prompt="What are my banking preferences and savings interests?",
                ),
                PromptCard(
                    eyebrow="Cached",
                    title="Fixed deposit rates",
                    prompt="What are your current fixed deposit interest rates?",
                ),
            ],
            theme=ThemeConfig(
                bg="#071a14",
                bg_accent_a="rgba(46, 204, 113, 0.12)",
                bg_accent_b="rgba(241, 196, 15, 0.08)",
                panel="rgba(12, 32, 26, 0.92)",
                panel_strong="rgba(14, 40, 32, 0.97)",
                panel_elevated="rgba(18, 48, 38, 0.95)",
                line="rgba(46, 204, 113, 0.15)",
                line_strong="rgba(241, 196, 15, 0.2)",
                text="#ecf7f2",
                muted="#8fb3a8",
                soft="#cfe8dc",
                accent="#2ecc71",
                user="#0d1f18",
                landing_bg="#F4F7F5",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="radish-bank",
            dataset_meta_key="radish-bank:meta:dataset",
            checkpoint_prefix="radish-bank:checkpoint",
            checkpoint_write_prefix="radish-bank:checkpoint_write",
            redis_instance_name="Radish Bank Redis Cloud",
            surface_name="Radish Bank Context Surface",
            agent_name="Radish Bank Service Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_bank_documents",
            status_text="Searching Radish Bank policy documents…",
            generating_text="Generating answer…",
            index_name_contains="bankdocument",
            vector_field="content_embedding",
            return_fields=["title", "category", "content", "document_id"],
            num_results=4,
            answer_system_prompt=(
                "You are Radish Bank's policy and product-information assistant. "
                "Answer using only the retrieved bank documents. If they do not cover the question, say so briefly."
            ),
        ),
        identity=IdentityConfig(
            default_id=DEMO_CUSTOMER_ID,
            default_name="Merv Kwok",
            default_email="merv.kwok@example.com",
            id_field="customer_id",
            description=(
                "Returns the signed-in retail customer id, name, and email. "
                "The customer_id is always the full string CUST001 in this demo—copy it exactly into any "
                "filter_*_by_customer_id or similar MCP tool (never shorten to C001). Call before account, card, or balance lookups."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="radish-guardrails",
            allowed_route_name="banking",
            routes=[
                GuardrailRouteConfig(
                    name="banking",
                    references=[
                        "Check my savings balance",
                        "What are my account balances?",
                        "Fixed deposit rate FD6",
                        "Waive annual card fee",
                        "Branch hours Tampines",
                        "Auto lobby and branch services",
                        "Accident insurance premium",
                        "Transfer between my accounts",
                        "Hello I need help with my account",
                        "What accounts do I have?",
                        "Early withdrawal penalty fixed deposit",
                        "What FD products are available?",
                        "What is the interest rate?",
                        "I want to invest in a fixed deposit",
                        "How do I open a new account?",
                        "What are the card fee charges?",
                        "Show me my service request history",
                        "Is Bishan a full branch?",
                        "What insurance plans do you offer?",
                        "Place 2000 SGD in the 6-month FD",
                        "Yes",
                        "No",
                        "Sure",
                        "Thanks",
                        "Hello",
                        "Can you help me?",
                    ],
                    distance_threshold=0.7,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "Why is the sky blue?",
                        "Who is the current US president?",
                        "Recipe for chocolate cake",
                        "Capital of Mongolia",
                        "Write me a Python sorting algorithm",
                        "What is the weather tomorrow?",
                        "Tell me a joke",
                        "History of the Roman Empire",
                        "Write a poem about love",
                        "What's the latest news?",
                        "Translate this to Spanish",
                        "Help me debug my code",
                        "What's the meaning of life?",
                        "Play a game with me",
                        "What's the stock market doing?",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(text="Prefers paperless statements and online banking", topics=["banking", "preferences"]),
            # SeedMemory(text="Interested in fixed deposit products for savings growth", topics=["products", "interests"]),
            SeedMemory(text="Use Savings Account for placing fixed deposits", topics=["fixed_deposit", "account"])
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="What are your current fixed deposit interest rates?",
                response=(
                    "We currently offer two fixed deposit plans:\n\n"
                    "- **FD6** (6-month term): **2.8% p.a.** — minimum deposit SGD 1,000\n"
                    "- **FD12** (12-month term): **3.1% p.a.** — minimum deposit SGD 1,000\n\n"
                    "Interest is calculated daily and paid at maturity. Early withdrawal forfeits all accrued interest. "
                    "You can open an FD through your account portal or visit any Radish Bank branch."
                ),
                attributes={"domain": "radish-bank"},
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def get_runtime_config(self, settings: Any) -> dict[str, Any]:
        memory_enabled = MemoryService(settings).is_configured() if settings else False
        return {
            "memory_enabled": memory_enabled,
            "memory_similarity_threshold": 0.5,
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
            "When the user refers to 'my savings', 'that waiver', or 'the Bishan branch', tie the answer to the "
            "exact account id, request id, or branch id from tool results. Do not invent rates or fees."
        )

    def describe_tool_trace_step(
        self,
        *,
        tool_name: str,
        payload: Any,
        runtime_config: dict[str, Any] | None = None,
    ) -> str | None:
        del runtime_config
        if tool_name == self.manifest.identity.tool_name:
            return "Resolve the authenticated Radish Bank customer before account or card lookups."
        if tool_name == "place_fixed_deposit":
            return "Validate FD amount, plan minimum, and funding balance before booking."
        if tool_name == "buy_accident_insurance":
            return "Check existing insurance holdings for duplicate coverage."
        if tool_name == "request_annual_card_fee_waiver":
            return "Check 12-month waiver history for this card fee category."
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
                description="Current UTC time (ISO) for comparing service-request timestamps.",
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description="Counts of Radish Bank demo entities loaded for this surface.",
            ),
            InternalToolDefinition(
                name="place_fixed_deposit",
                description=(
                    "Place a fixed deposit below SGD 10,000 from an active account. "
                    "Inputs: plan_id (FD6|FD12), amount_sgd (number), funding_account_id."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string"},
                        "amount_sgd": {"type": "number"},
                        "funding_account_id": {"type": "string"},
                    },
                    "required": ["plan_id", "amount_sgd", "funding_account_id"],
                },
            ),
            InternalToolDefinition(
                name="buy_accident_insurance",
                description="Purchase accident insurance by plan_id (INS_BASIC or INS_PLUS) if not already held.",
                input_schema={
                    "type": "object",
                    "properties": {"plan_id": {"type": "string"}},
                    "required": ["plan_id"],
                },
            ),
            InternalToolDefinition(
                name="request_annual_card_fee_waiver",
                description="Request a waiver for CARD001 annual fee; approved once per rolling 12 months.",
                input_schema={
                    "type": "object",
                    "properties": {"card_id": {"type": "string"}},
                    "required": ["card_id"],
                },
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
                                    "description": "Optional topic tags like banking, preferences, products, insurance.",
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
            raw_id = (os.getenv(identity.id_env_var) or identity.default_id).strip()
            # Demo seed + indexes use CUST001; tolerate common .env typo "C001".
            customer_id = DEMO_CUSTOMER_ID if raw_id.casefold() == "c001" else raw_id
            return {
                identity.id_field: customer_id,
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
            }
        if tool_name == "get_current_time":
            now = datetime.now(timezone.utc)
            return {"current_time": now.isoformat(), "timezone": "UTC"}
        if tool_name == "dataset_overview":
            client = create_redis_client(settings)
            raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
            if raw:
                data = json.loads(raw)
                return data[0] if isinstance(data, list) else data
            return {"error": "Dataset metadata not found. Run the data loader first."}
        if tool_name == "place_fixed_deposit":
            return self._place_fixed_deposit(arguments, settings)
        if tool_name == "buy_accident_insurance":
            return self._buy_accident_insurance(arguments, settings)
        if tool_name == "request_annual_card_fee_waiver":
            return self._request_fee_waiver(arguments, settings)
        return {"error": f"Unknown tool: {tool_name}"}

    async def aexecute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name not in {"search_customer_memory", "remember_customer_detail"}:
            return await asyncio.to_thread(self.execute_internal_tool, tool_name, arguments, settings)

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

    def _place_fixed_deposit(self, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        gm = _load_generated_models()
        plan_id = str(arguments.get("plan_id", "")).strip()
        funding = str(arguments.get("funding_account_id", "")).strip()
        try:
            amount = float(arguments.get("amount_sgd"))
        except (TypeError, ValueError):
            return {"status": "rejected", "message": "amount_sgd must be a number."}

        out = OUTPUT_DIR
        plans = {r["plan_id"]: r for r in _read_jsonl(out / "fixed_deposit_plans.jsonl")}
        accounts = _read_jsonl(out / "accounts.jsonl")
        holdings = _read_jsonl(out / "product_holdings.jsonl")
        requests = _read_jsonl(out / "service_requests.jsonl")

        if amount >= 10000:
            return {"status": "rejected", "message": "Amount must be below SGD 10,000 for this demo."}
        if plan_id not in plans:
            return {"status": "rejected", "message": f"Unknown plan_id {plan_id!r}."}
        plan = plans[plan_id]
        if amount < int(plan["min_deposit_sgd"]):
            return {"status": "rejected", "message": f"Amount below minimum {plan['min_deposit_sgd']} SGD."}

        acct = next((a for a in accounts if a["account_id"] == funding), None)
        if not acct:
            return {"status": "rejected", "message": f"Unknown funding account {funding!r}."}
        if acct.get("customer_id") != DEMO_CUSTOMER_ID:
            return {"status": "rejected", "message": "Funding account does not belong to the demo customer."}
        if float(acct["balance_sgd"]) < amount:
            return {"status": "rejected", "message": "Insufficient balance on the funding account."}

        label = f"{plan['tenure_months']}M Fixed Deposit"
        hid = _next_id("HOLD", holdings, "holding_id")
        rid = _next_id("REQ", requests, "request_id")
        now = datetime.now(timezone.utc).isoformat()

        acct["balance_sgd"] = round(float(acct["balance_sgd"]) - amount, 2)
        accounts = [a if a["account_id"] != funding else acct for a in accounts]
        holdings.append(
            {
                "holding_id": hid,
                "customer_id": DEMO_CUSTOMER_ID,
                "product_type": "fixed_deposit",
                "product_name": label,
                "status": "active",
            }
        )
        requests.append(
            {
                "request_id": rid,
                "customer_id": DEMO_CUSTOMER_ID,
                "request_type": "fixed_deposit",
                "status": "approved",
                "created_at": now,
            }
        )
        _write_jsonl(out / "accounts.jsonl", accounts)
        _write_jsonl(out / "product_holdings.jsonl", holdings)
        _write_jsonl(out / "service_requests.jsonl", requests)

        acc_m = gm.Account(**acct)
        hold_m = gm.ProductHolding(**holdings[-1])
        req_m = gm.ServiceRequest(**requests[-1])
        imp = {
            "Account": _run_import(settings, [acc_m]),
            "ProductHolding": _run_import(settings, [hold_m]),
            "ServiceRequest": _run_import(settings, [req_m]),
        }

        return {
            "status": "approved",
            "message": f"Placed {amount} SGD into {label} from {funding}.",
            "updated_records": [funding, hid, rid],
            "import": imp,
        }

    def _buy_accident_insurance(self, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        gm = _load_generated_models()
        plan_id = str(arguments.get("plan_id", "")).strip()
        out = OUTPUT_DIR
        plans = {r["plan_id"]: r for r in _read_jsonl(out / "insurance_plans.jsonl")}
        holdings = _read_jsonl(out / "product_holdings.jsonl")
        requests = _read_jsonl(out / "service_requests.jsonl")

        if plan_id not in plans:
            return {"status": "rejected", "message": f"Unknown insurance plan {plan_id!r}."}
        name = str(plans[plan_id]["plan_name"])
        if any(
            h.get("product_type") == "insurance" and h.get("product_name") == name for h in holdings
        ):
            return {"status": "rejected", "message": "Customer already holds this insurance plan."}

        hid = _next_id("HOLD", holdings, "holding_id")
        rid = _next_id("REQ", requests, "request_id")
        now = datetime.now(timezone.utc).isoformat()
        holdings.append(
            {
                "holding_id": hid,
                "customer_id": DEMO_CUSTOMER_ID,
                "product_type": "insurance",
                "product_name": name,
                "status": "active",
            }
        )
        requests.append(
            {
                "request_id": rid,
                "customer_id": DEMO_CUSTOMER_ID,
                "request_type": "insurance",
                "status": "approved",
                "created_at": now,
            }
        )
        _write_jsonl(out / "product_holdings.jsonl", holdings)
        _write_jsonl(out / "service_requests.jsonl", requests)

        hold_m = gm.ProductHolding(**holdings[-1])
        req_m = gm.ServiceRequest(**requests[-1])
        imp = {
            "ProductHolding": _run_import(settings, [hold_m]),
            "ServiceRequest": _run_import(settings, [req_m]),
        }
        return {
            "status": "approved",
            "message": f"Purchased {name}.",
            "updated_records": [hid, rid],
            "import": imp,
        }

    def _request_fee_waiver(self, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        gm = _load_generated_models()
        card_id = str(arguments.get("card_id", "")).strip()
        if card_id != "CARD001":
            return {"status": "rejected", "message": "This demo only supports CARD001."}

        out = OUTPUT_DIR
        requests = _read_jsonl(out / "service_requests.jsonl")
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=365)

        recent_ok = False
        for r in requests:
            if (
                r.get("customer_id") == DEMO_CUSTOMER_ID
                and r.get("request_type") == "annual_card_fee_waiver"
                and r.get("status") == "approved"
            ):
                try:
                    created = _parse_iso(str(r["created_at"]))
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if created >= window_start:
                        recent_ok = True
                        break
                except ValueError:
                    continue

        rid = _next_id("REQ", requests, "request_id")
        status = "rejected" if recent_ok else "approved"
        msg = (
            "An annual fee waiver was already approved within the last 12 months."
            if recent_ok
            else "Annual card fee waiver approved for this cycle."
        )
        requests.append(
            {
                "request_id": rid,
                "customer_id": DEMO_CUSTOMER_ID,
                "request_type": "annual_card_fee_waiver",
                "status": status,
                "created_at": now.isoformat(),
            }
        )
        _write_jsonl(out / "service_requests.jsonl", requests)
        req_m = gm.ServiceRequest(**requests[-1])
        imp = _run_import(settings, [req_m])
        return {
            "status": status,
            "message": msg,
            "updated_records": [rid],
            "import": imp,
        }

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        summary = {
            "customers": len(records.get("Customer", [])),
            "accounts": len(records.get("Account", [])),
            "cards": len(records.get("Card", [])),
            "fixed_deposit_plans": len(records.get("FixedDepositPlan", [])),
            "insurance_plans": len(records.get("InsurancePlan", [])),
            "branches": len(records.get("Branch", [])),
            "branch_hours": len(records.get("BranchHours", [])),
            "product_holdings": len(records.get("ProductHolding", [])),
            "service_requests": len(records.get("ServiceRequest", [])),
            "bank_documents": len(records.get("BankDocument", [])),
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


DOMAIN = RadishBankDomain()
