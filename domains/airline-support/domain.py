from __future__ import annotations

import importlib.util
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
from backend.app.redis_connection import create_redis_client
from backend.app.request_context import get_demo_user_id

ROOT = Path(__file__).resolve().parents[2]


def _load_local_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(f"airline_support_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load airline-support module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")

DEMO_PROFILE = _data_generator.DEMO_PROFILE
CUSTOMER_PROFILES = _data_generator.CUSTOMER_PROFILES
DATASET_SUMMARY = _data_generator.DATASET_SUMMARY
generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS
CACHE_SAFE_SERVICE_PERMISSION_FIELDS = (
    "operational_alerts",
    "self_service_rebooking",
    "priority_service_routing",
)


def _cache_safe_service_permissions(profile: dict[str, Any]) -> dict[str, bool]:
    permissions = profile.get("service_permissions")
    if not isinstance(permissions, dict):
        permissions = DEMO_PROFILE["service_permissions"]
    return {
        field: bool(permissions.get(field, False))
        for field in CACHE_SAFE_SERVICE_PERMISSION_FIELDS
    }


class AirlineSupportDomain:
    manifest = DomainManifest(
        id="airline-support",
        description=(
            "General airline support demo focused on flight status, disruption handling, "
            "and traveller profile lookup."
        ),
        generated_models_module="domains.airline-support.generated_models",
        generated_models_path="domains/airline-support/generated_models.py",
        output_dir="output/airline-support",
        branding=BrandingConfig(
            app_name="Aurora Air",
            subtitle="Digital assistant",
            hero_title="Aurora Air",
            placeholder_text="Ask about your trip",
            logo_path="domains/airline-support/assets/logo.svg",
            demo_steps=[
                "My flight was disrupted. What happened?",
                "Can I still check in for the new flight?",
                "What help do I usually get after a cancellation?",
                "What is the status of ZX018 today?",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Flight Status",
                    title="Flight ZX018",
                    prompt="What is the status of ZX018 today?",
                ),
                PromptCard(
                    eyebrow="Disruption Help",
                    title="Delays and cancellations",
                    prompt="My flight was disrupted. What happened?",
                ),
                PromptCard(
                    eyebrow="Trip Changes",
                    title="Rebooking",
                    prompt="What are my rebooking options?",
                ),
                PromptCard(
                    eyebrow="Status Benefits",
                    title="After-cancellation help",
                    prompt="What help do I usually get after a cancellation?",
                ),
            ],
            theme=ThemeConfig(
                bg="#f7fbff",
                bg_accent_a="rgba(255, 204, 0, 0.16)",
                bg_accent_b="rgba(20, 67, 114, 0.10)",
                panel="rgba(255, 255, 255, 0.92)",
                panel_strong="rgba(255, 255, 255, 0.98)",
                panel_elevated="rgba(245, 249, 255, 0.98)",
                line="rgba(20, 67, 114, 0.08)",
                line_strong="rgba(20, 67, 114, 0.18)",
                text="#102a43",
                muted="#5f7892",
                soft="#294661",
                accent="#ffcc00",
                user="#dcebf8",
                landing_bg="#EAF5FF",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="airline_support",
            dataset_meta_key="airline_support:meta:dataset",
            checkpoint_prefix="airline_support:checkpoint",
            checkpoint_write_prefix="airline_support:checkpoint_write",
            redis_instance_name="Airline Support Redis Cloud",
            surface_name="Airline Support Surface",
            agent_name="Airline Support Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_travel_policies",
            status_text="Searching travel guidance…",
            generating_text="Preparing answer…",
            index_name_contains="travel",
            vector_field="content_embedding",
            return_fields=["title", "category", "content"],
            num_results=3,
            answer_system_prompt=(
                "You are the airline digital assistant in Simple RAG mode. "
                "Answer only from the provided traveller-profile and travel-policy documents. "
                "Start by summarizing the most relevant guidance from those documents in plain language. "
                "For disruption questions, explain the general policy outcome when the documents support it, "
                "such as automatic rebooking, refund guidance, baggage handling, or check-in implications. "
                "Be explicit that in Simple RAG mode you cannot see the traveller's live booking, flight, or disruption records, "
                "so you cannot confirm what happened to their specific trip. "
                "Do not claim access to personal or operational records. "
                "If the documents do not contain the answer, say so plainly."
            ),
        ),
        identity=IdentityConfig(
            id_field="customer_id",
            default_id=DEMO_PROFILE["customer_id"],
            default_name=DEMO_PROFILE["display_name"],
            default_email=DEMO_PROFILE["email"],
            description=(
                "Returns the signed-in traveller context for self-service support, including customer ID, "
                "profile reference, status tier, language, read-only contact details, and service-permission flags."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="airline-support-guardrails",
            allowed_route_name="airline_support",
            routes=[
                GuardrailRouteConfig(
                    name="airline_support",
                    references=[
                        "My flight was disrupted. What happened?",
                        "Can I still check in for the new flight?",
                        "What are my rebooking options?",
                        "What help do I usually get after a cancellation?",
                        "What is the status of ZX018 today?",
                        "Which terminal is my flight departing from?",
                        "Will my baggage still go to New York?",
                        "What does my travel profile say about my status?",
                        "What contact details do you have on file for me?",
                        "Show me my updated itinerary",
                        "Do I need to do anything next?",
                        "How do cancellations and automatic rebooking work?",
                        "What baggage guidance applies after a same-day rebooking?",
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
                        "Generate an image of an airplane",
                        "What is the capital of France?",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(
                text="Traveller is a Senator tier member who prefers English support",
                topics=["airline", "loyalty", "preferences"],
            ),
            SeedMemory(
                text="Traveller wants clear operational next steps after same-day disruptions",
                topics=["airline", "disruption", "support_preferences"],
            ),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="What is the status of ZX018 today?",
                response=(
                    "ZX018 is the shared Aurora Air operating flight from Frankfurt to Hamburg. "
                    "It is currently on time from Terminal 1, with no gate assigned yet."
                ),
                attributes={
                    "domain": "airline-support",
                    "access_class": "public",
                    "topic": "shared_flight_status",
                },
            ),
            SeedLangCacheEntry(
                prompt="What help do I usually get after a cancellation?",
                response=(
                    "For status-tier cancellation support, Aurora Air normally combines automatic rebooking, "
                    "priority service routing where available, and policy guidance for check-in, baggage, and airport help. "
                    "Use the traveller's tier context before making this guidance specific."
                ),
                attributes={
                    "domain": "airline-support",
                    "access_class": "group",
                    "cache_group_id": "senator_en",
                    "topic": "status_tier_disruption_help",
                },
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def get_runtime_config(self, *, settings: Any) -> dict[str, Any]:
        del settings
        return {}

    def get_demo_users(self) -> list[dict[str, str]]:
        return [
            {
                "id": str(profile["customer_id"]),
                "label": str(profile["display_name"]),
                "subtitle": f"{profile['status_tier']} • {profile['preferred_language']}",
                "cache_group_id": str(profile["cache_group_id"]),
            }
            for profile in CUSTOMER_PROFILES
        ]

    def resolve_demo_user(self, demo_user_id: str | None) -> dict[str, Any] | None:
        if not demo_user_id:
            return dict(DEMO_PROFILE)
        for profile in CUSTOMER_PROFILES:
            if profile["customer_id"] == demo_user_id:
                return dict(profile)
        return None

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        return build_system_prompt(mcp_tools=mcp_tools, runtime_config=runtime_config)

    def build_answer_verifier_prompt(self, *, runtime_config: dict[str, Any] | None = None) -> str:
        del runtime_config
        return ""

    def classify_mcp_semantic_cache_access(self, tool_name: str) -> str:
        if tool_name.startswith("search_travelpolicydoc_by_text"):
            return "public"
        if tool_name.startswith("filter_operatingflight_by_flight_number"):
            return "public"
        if tool_name.startswith("filter_customerprofile_by_") or tool_name.startswith("search_customerprofile_by_"):
            return "non-cacheable"
        if (
            tool_name.startswith("filter_booking_by_")
            or tool_name.startswith("search_booking_by_")
            or tool_name.startswith("filter_itinerarysegment_by_")
            or tool_name.startswith("filter_operationaldisruption_by_")
            or tool_name.startswith("filter_reaccommodationrecord_by_")
            or tool_name.startswith("filter_supportcase_by_")
            or tool_name.startswith("filter_operatingflight_by_operating_flight_id")
        ):
            return "non-cacheable"
        return "ignored"

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
            for key in ("value", "query", "booking_id", "flight_number", "customer_id"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in traveller before looking up bookings, operational disruptions, or profile details."
        if tool_name == "get_current_service_tier_context":
            return "Read the traveller's cache-safe tier and service-permission context for cohort-level benefit guidance."
        if tool_name == "get_current_time":
            return "Anchor the answer against the current UTC time before comparing trip dates or next steps."
        if tool_name == "dataset_overview":
            return "Check the current airline demo coverage before reasoning about available records."
        if tool_name.startswith("filter_booking_by_customer_id"):
            return "Load the traveller's bookings and find the most relevant trip for this question."
        if tool_name.startswith("filter_itinerarysegment_by_booking_id"):
            return "Inspect the exact itinerary segments for the selected booking."
        if tool_name.startswith("filter_itinerarysegment_by_flight_number"):
            return f"Look up the booked itinerary segment for flight {detail or 'the requested flight'}."
        if tool_name.startswith("filter_operatingflight_by_operating_flight_id"):
            return "Read the shared operating flight record for the selected itinerary segment."
        if tool_name.startswith("filter_operatingflight_by_flight_number"):
            return f"Read the shared operating flight record for flight {detail or 'the requested flight'}."
        if tool_name.startswith("filter_operationaldisruption_by_"):
            return "Read the operational disruption event so the answer reflects what happened to the flight."
        if tool_name.startswith("filter_reaccommodationrecord_by_"):
            return "Read the reaccommodation record so the answer reflects how the traveller was reassigned."
        if tool_name.startswith("filter_supportcase_by_"):
            return "Check whether support already opened a case for this traveller or booking."
        if tool_name.startswith("search_travelpolicydoc_by_text"):
            return f"Pull policy guidance to supplement the record-backed answer: {detail or 'travel policy search'}."
        return None

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        del runtime_config
        return (
            InternalToolDefinition(
                name=self.manifest.identity.tool_name,
                description=self.manifest.identity.description,
            ),
            InternalToolDefinition(
                name="get_current_service_tier_context",
                description=(
                    "Returns cache-safe cohort context for the signed-in traveller, including status tier, "
                    "preferred language, service permissions, and cache group. Use this for tier-level benefit questions."
                ),
            ),
            InternalToolDefinition(
                name="get_current_time",
                description=(
                    "Returns the current date and time in UTC (ISO 8601). "
                    "Use this to compare against departure times, disruption timelines, and next-step windows."
                ),
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description=(
                    "Returns record counts for the airline demo dataset, including profiles, bookings, itinerary segments, "
                    "operating flights, operational disruptions, reaccommodation records, support cases, and travel policy documents."
                ),
            ),
        )

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        del arguments
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            request_demo_user_id = get_demo_user_id()
            profile = self.resolve_demo_user(request_demo_user_id or os.getenv(identity.id_env_var)) or DEMO_PROFILE
            display_name = str(profile.get("display_name", identity.default_name))
            email = str(profile.get("email", identity.default_email))
            if not request_demo_user_id:
                display_name = os.getenv(identity.name_env_var, display_name)
                email = os.getenv(identity.email_env_var, email)
            return {
                identity.id_field: str(profile.get(identity.id_field, identity.default_id)),
                "display_name": display_name,
                "email": email,
                "profile_reference": str(profile.get("profile_reference", DEMO_PROFILE["profile_reference"])),
                "ticket_name_masked": str(profile.get("ticket_name_masked", DEMO_PROFILE["ticket_name_masked"])),
                "loyalty_member_id_masked": str(
                    profile.get("loyalty_member_id_masked", DEMO_PROFILE["loyalty_member_id_masked"])
                ),
                "salutation": str(profile.get("salutation", DEMO_PROFILE["salutation"])),
                "birth_date": str(profile.get("birth_date", DEMO_PROFILE["birth_date"])),
                "gender": str(profile.get("gender", DEMO_PROFILE["gender"])),
                "status_tier": str(profile.get("status_tier", DEMO_PROFILE["status_tier"])),
                "preferred_language": str(profile.get("preferred_language", DEMO_PROFILE["preferred_language"])),
                "customer_program": str(profile.get("customer_program", DEMO_PROFILE["customer_program"])),
                "customer_usage": str(profile.get("customer_usage", DEMO_PROFILE["customer_usage"])),
                "enrollment_carrier": str(
                    profile.get("enrollment_carrier", DEMO_PROFILE["enrollment_carrier"])
                ),
                "service_permissions": profile.get("service_permissions", DEMO_PROFILE["service_permissions"]),
                "cache_group_id": str(profile.get("cache_group_id", DEMO_PROFILE["cache_group_id"])),
            }
        if tool_name == "get_current_service_tier_context":
            profile = self.resolve_demo_user(get_demo_user_id() or os.getenv(self.manifest.identity.id_env_var)) or DEMO_PROFILE
            return {
                "status_tier": str(profile.get("status_tier", DEMO_PROFILE["status_tier"])),
                "preferred_language": str(profile.get("preferred_language", DEMO_PROFILE["preferred_language"])),
                "customer_program": str(profile.get("customer_program", DEMO_PROFILE["customer_program"])),
                "service_permissions": _cache_safe_service_permissions(profile),
                "cache_group_id": str(profile.get("cache_group_id", DEMO_PROFILE["cache_group_id"])),
            }
        if tool_name == "get_current_time":
            now = datetime.now(timezone.utc)
            return {"current_time": now.isoformat(), "timezone": "UTC"}
        if tool_name == "dataset_overview":
            if settings is not None:
                client = None
                try:
                    client = create_redis_client(settings)
                    raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
                    if raw:
                        data = json.loads(raw)
                        return data[0] if isinstance(data, list) else data
                except Exception:
                    pass
                finally:
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            pass
            return dict(DATASET_SUMMARY)
        return {"error": f"Unknown tool: {tool_name}"}

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        summary = {
            "customer_profiles": len(records.get("CustomerProfile", [])),
            "bookings": len(records.get("Booking", [])),
            "itinerary_segments": len(records.get("ItinerarySegment", [])),
            "operating_flights": len(records.get("OperatingFlight", [])),
            "operational_disruptions": len(records.get("OperationalDisruption", [])),
            "reaccommodation_records": len(records.get("ReaccommodationRecord", [])),
            "support_cases": len(records.get("SupportCase", [])),
            "travel_policy_docs": len(records.get("TravelPolicyDoc", [])),
        }
        if settings is not None:
            client = None
            try:
                client = create_redis_client(settings)
                client.execute_command(
                    "JSON.SET",
                    self.manifest.namespace.dataset_meta_key,
                    "$",
                    json.dumps(summary, ensure_ascii=False),
                )
            except Exception:
                pass
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
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


DOMAIN = AirlineSupportDomain()
