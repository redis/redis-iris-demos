from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from backend.app.core.domain_contract import (
    GeneratedDataset,
    InternalToolDefinition,
)
from backend.app.core.domain_schema import EntitySpec, validate_entity_specs
from backend.app.redis_connection import create_redis_client
from backend.app.request_context import get_demo_user_id
from domains.banking_core.config import BankingDemoConfig
from domains.banking_core.data_generator import BankingDemoBundle

ROOT = Path(__file__).resolve().parents[2]
CACHE_SAFE_SERVICE_PERMISSION_FIELDS = (
    "secure_app_messaging",
    "instant_card_controls",
    "priority_support_routing",
)


def _cache_safe_service_permissions(profile: dict[str, Any], fallback: dict[str, Any]) -> dict[str, bool]:
    permissions = profile.get("service_permissions")
    if not isinstance(permissions, dict):
        permissions = fallback.get("service_permissions", {})
    return {
        field: bool(permissions.get(field, False))
        for field in CACHE_SAFE_SERVICE_PERMISSION_FIELDS
    }


@dataclass(frozen=True)
class BankingDomainResources:
    bundle: BankingDemoBundle
    prompt_builder: Callable[..., str]
    generate_demo_data_fn: Callable[..., GeneratedDataset]


class BankingSupportDomainBase:
    def __init__(
        self,
        *,
        config: BankingDemoConfig,
        manifest: Any,
        entity_specs: tuple[EntitySpec, ...],
        resources: BankingDomainResources,
    ) -> None:
        self.config = config
        self.manifest = manifest
        self._entity_specs = entity_specs
        self._resources = resources

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return self._entity_specs

    def get_runtime_config(self, *, settings: Any) -> dict[str, Any]:
        del settings
        return {}

    def get_demo_users(self) -> list[dict[str, str]]:
        return [
            {
                "id": str(profile["customer_id"]),
                "label": str(profile["display_name"]),
                "subtitle": f"{profile['customer_segment']} • {profile['preferred_language']}",
                "cache_group_id": str(profile["cache_group_id"]),
            }
            for profile in self._resources.bundle.customer_profiles
        ]

    def resolve_demo_user(self, demo_user_id: str | None) -> dict[str, Any] | None:
        if not demo_user_id:
            return dict(self._resources.bundle.demo_profile)
        for profile in self._resources.bundle.customer_profiles:
            if profile["customer_id"] == demo_user_id:
                return dict(profile)
        return dict(self._resources.bundle.demo_profile)

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        del runtime_config
        return self._resources.prompt_builder(
            mcp_tools=mcp_tools,
            bank_name=self.config.bank_name,
            mobile_app_name=self.config.mobile_app_name,
            app_service_name=self.config.app_service_name,
            payments_service_name=self.config.payments_service_name,
            plus_segment=self.config.plus_segment,
            standard_segment=self.config.standard_segment,
        )

    def build_answer_verifier_prompt(self, *, runtime_config: dict[str, Any] | None = None) -> str:
        del runtime_config
        return ""

    def classify_mcp_semantic_cache_access(self, tool_name: str) -> str:
        if tool_name.startswith("search_supportguidancedoc_by_text"):
            return "public"
        if tool_name.startswith("filter_servicestatus_by_"):
            return "public"
        if tool_name.startswith("filter_customerprofile_by_") or tool_name.startswith("search_customerprofile_by_"):
            return "non-cacheable"
        if (
            tool_name.startswith("filter_depositaccount_by_")
            or tool_name.startswith("filter_debitcard_by_")
            or tool_name.startswith("filter_cardauthorisation_by_")
            or tool_name.startswith("filter_cardriskevent_by_")
            or tool_name.startswith("filter_cardsupportintervention_by_")
            or tool_name.startswith("filter_cardrecoveryoption_by_")
            or tool_name.startswith("filter_supportcase_by_")
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
            for key in ("value", "query", "account_id", "selected_option_code", "customer_id"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in customer before looking up account, card, or support details."
        if tool_name == "get_current_customer_support_context":
            return "Read the customer's cache-safe segment and service-permission context for cohort-level support guidance."
        if tool_name == "get_current_time":
            return "Anchor the answer against the current UTC time before comparing review windows or service updates."
        if tool_name == "dataset_overview":
            return "Check the current banking demo coverage before reasoning about available records."
        if tool_name.startswith("filter_depositaccount_by_customer_id"):
            return "Load the customer's deposit accounts and find the most relevant account for this support question."
        if tool_name.startswith("filter_debitcard_by_account_id"):
            return "Inspect the debit cards attached to the selected account."
        if tool_name.startswith("filter_debitcard_by_card_last4"):
            return f"Look up the specific debit card ending {detail or 'the requested digits'}."
        if tool_name.startswith("filter_cardauthorisation_by_"):
            return "Read the card authorisation records so the answer reflects the actual declined or approved transaction."
        if tool_name.startswith("filter_cardriskevent_by_"):
            return f"Read the risk event so the answer reflects why {self.config.bank_name} flagged the card activity."
        if tool_name.startswith("filter_cardsupportintervention_by_"):
            return f"Read the active safeguard so the answer reflects what {self.config.bank_name} already did to the card."
        if tool_name.startswith("filter_cardrecoveryoption_by_"):
            return "Read the customer-facing recovery options so the customer can compare the available next steps."
        if tool_name.startswith("filter_supportcase_by_"):
            return "Check whether support already opened or updated a case for this customer."
        if tool_name == "submit_card_recovery_selection":
            return "Confirm the customer's selected recovery option for the safeguarded account."
        if tool_name.startswith("filter_servicestatus_by_"):
            return f"Read the shared service-status record for {detail or 'the requested service'}."
        if tool_name.startswith("search_supportguidancedoc_by_text"):
            return f"Pull shared support guidance to supplement the record-backed answer: {detail or 'support guidance search'}."
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
                name="get_current_customer_support_context",
                description=(
                    "Returns cache-safe cohort context for the signed-in banking customer, including segment, "
                    "support plan, preferred language, service permissions, and cache group. Use this for segment-level "
                    "support-routing guidance."
                ),
            ),
            InternalToolDefinition(
                name="submit_card_recovery_selection",
                description=(
                    "Confirms a customer-selected card recovery option for a specific deposit account. "
                    "Call get_current_user_profile and then filter_depositaccount_by_customer_id in the same turn immediately before "
                    "this tool, and pass the exact account_id returned by that account lookup. This is a realistic demo action "
                    "that validates the selected recovery option and returns a confirmation payload, but it does not persist any live "
                    "card or account change."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "selected_option_code": {"type": "string"},
                        "confirm_change": {"type": "boolean"},
                    },
                    "required": ["account_id", "selected_option_code", "confirm_change"],
                },
            ),
            InternalToolDefinition(
                name="get_current_time",
                description=(
                    "Returns the current date and time in UTC (ISO 8601). "
                    "Use this to compare against card-control timelines, review windows, and service-status updates."
                ),
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description=(
                    "Returns record counts for the consumer banking dataset, including profiles, deposit accounts, debit cards, "
                    "card authorisations, card risk events, support interventions, recovery options, support cases, service-status records, "
                    "and support guidance documents."
                ),
            ),
        )

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        bundle = self._resources.bundle
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            request_demo_user_id = get_demo_user_id()
            profile = self.resolve_demo_user(request_demo_user_id or os.getenv(identity.id_env_var)) or bundle.demo_profile
            display_name = str(profile.get("display_name", identity.default_name))
            email = str(profile.get("email", identity.default_email))
            if not request_demo_user_id:
                display_name = os.getenv(identity.name_env_var, display_name)
                email = os.getenv(identity.email_env_var, email)
            return {
                identity.id_field: str(profile.get(identity.id_field, identity.default_id)),
                "display_name": display_name,
                "email": email,
                "profile_reference": str(profile.get("profile_reference", bundle.demo_profile["profile_reference"])),
                "salutation": str(profile.get("salutation", bundle.demo_profile["salutation"])),
                "customer_segment": str(profile.get("customer_segment", bundle.demo_profile["customer_segment"])),
                "support_plan": str(profile.get("support_plan", bundle.demo_profile["support_plan"])),
                "preferred_language": str(profile.get("preferred_language", bundle.demo_profile["preferred_language"])),
                "mobile_number_masked": str(profile.get("mobile_number_masked", bundle.demo_profile["mobile_number_masked"])),
                "postal_region_prefix": str(profile.get("postal_region_prefix", bundle.demo_profile["postal_region_prefix"])),
                "service_permissions": profile.get("service_permissions", bundle.demo_profile["service_permissions"]),
                "cache_group_id": str(profile.get("cache_group_id", bundle.demo_profile["cache_group_id"])),
            }
        if tool_name == "get_current_customer_support_context":
            profile = self.resolve_demo_user(get_demo_user_id() or os.getenv(self.manifest.identity.id_env_var)) or bundle.demo_profile
            service_permissions = _cache_safe_service_permissions(profile, bundle.demo_profile)
            support_plan = str(profile.get("support_plan", bundle.demo_profile["support_plan"]))
            customer_segment = str(profile.get("customer_segment", bundle.demo_profile["customer_segment"]))
            routing_summary = (
                f"{support_plan} includes priority support routing and appointment-style follow-up when appropriate."
                if service_permissions.get("priority_support_routing")
                else f"{support_plan} uses the standard app and phone support route."
            )
            return {
                "customer_segment": customer_segment,
                "support_plan": support_plan,
                "preferred_language": str(profile.get("preferred_language", bundle.demo_profile["preferred_language"])),
                "service_permissions": service_permissions,
                "routing_summary": routing_summary,
                "cache_group_id": str(profile.get("cache_group_id", bundle.demo_profile["cache_group_id"])),
            }
        if tool_name == "submit_card_recovery_selection":
            account_id = str(arguments.get("account_id") or "").strip()
            selected_option_code = str(arguments.get("selected_option_code") or "").strip()
            confirm_change = arguments.get("confirm_change")
            active_profile = self.resolve_demo_user(get_demo_user_id() or os.getenv(self.manifest.identity.id_env_var)) or bundle.demo_profile
            active_customer_id = str(active_profile.get(self.manifest.identity.id_field, bundle.demo_profile["customer_id"]))

            if not account_id or not selected_option_code:
                return {
                    "status": "error",
                    "error_code": "MISSING_CARD_RECOVERY_SELECTION",
                    "message": "account_id and selected_option_code are required.",
                }
            if confirm_change is not True:
                return {
                    "status": "error",
                    "error_code": "CARD_RECOVERY_CONFIRMATION_REQUIRED",
                    "message": "confirm_change must be true before the demo can confirm the selected card recovery option.",
                }

            matching_accounts = [
                item
                for item in bundle.deposit_accounts
                if item["account_id"] == account_id and item["customer_id"] == active_customer_id
            ]
            if not matching_accounts:
                return {
                    "status": "error",
                    "error_code": "CARD_RECOVERY_ACCOUNT_MISMATCH",
                    "message": "The selected account does not belong to the signed-in customer.",
                }

            normalized_selection = selected_option_code.upper()
            normalized_label = " ".join(selected_option_code.lower().split())

            matching_options = [
                item
                for item in bundle.card_recovery_options
                if item["account_id"] == account_id
                and (
                    item["option_code"] == normalized_selection
                    or " ".join(str(item["option_label"]).lower().split()) == normalized_label
                )
            ]
            if not matching_options:
                return {
                    "status": "error",
                    "error_code": "INVALID_CARD_RECOVERY_OPTION",
                    "message": "The selected recovery option does not match this account.",
                }
            if len(matching_options) > 1:
                return {
                    "status": "error",
                    "error_code": "AMBIGUOUS_CARD_RECOVERY_OPTION",
                    "message": "Multiple recovery options matched this option code for this account.",
                }
            option = matching_options[0]
            current_option = next(
                (
                    item
                    for item in bundle.card_recovery_options
                    if item["account_id"] == account_id and item["option_type"] == "currently_applied"
                ),
                None,
            )
            from_option_code = str(current_option["option_code"]) if current_option else ""
            return {
                "status": "confirmed",
                "request_id": f"CARD_RECOVERY_REQ_{option['option_id']}",
                "account_id": account_id,
                "selected_option_id": option["option_id"],
                "from_option_code": from_option_code,
                "to_option_code": str(option["option_code"]),
                "effective_status_summary": option["expected_outcome"],
                "customer_message": (
                    f"Your {self.config.bank_name} card-support selection for {option['option_label'].lower()} has been confirmed in this demo. "
                    "Your account remains the same."
                ),
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
            return dict(bundle.summary)
        return {"error": f"Unknown tool: {tool_name}"}

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        summary = {
            "customer_profiles": len(records.get("CustomerProfile", [])),
            "deposit_accounts": len(records.get("DepositAccount", [])),
            "debit_cards": len(records.get("DebitCard", [])),
            "card_authorisations": len(records.get("CardAuthorisation", [])),
            "card_risk_events": len(records.get("CardRiskEvent", [])),
            "card_support_interventions": len(records.get("CardSupportIntervention", [])),
            "card_recovery_options": len(records.get("CardRecoveryOption", [])),
            "support_cases": len(records.get("SupportCase", [])),
            "service_statuses": len(records.get("ServiceStatus", [])),
            "support_guidance_docs": len(records.get("SupportGuidanceDoc", [])),
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
        return self._resources.generate_demo_data_fn(
            config=self.config,
            bundle=self._resources.bundle,
            output_dir=output_dir,
            seed=seed,
            update_env_file=update_env_file,
        )

    def validate(self) -> list[str]:
        errors = validate_entity_specs(self.get_entity_specs())
        if not (ROOT / self.manifest.branding.logo_path).exists():
            errors.append(f"Logo file not found: {self.manifest.branding.logo_path}")
        if not self.manifest.branding.starter_prompts:
            errors.append("Branding must define at least one starter prompt")
        return errors
