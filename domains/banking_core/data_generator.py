"""Reusable sample-data helpers for consumer-banking demo domains."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

from backend.app.core.domain_contract import GeneratedDataset
from domains.banking_core.config import BankingDemoConfig

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ts(dt: datetime) -> str:
    return dt.isoformat()


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    try:
        client = openai.OpenAI()
        response = client.embeddings.create(
            input=texts,
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return [item.embedding for item in response.data]
    except Exception:
        return [fake_embedding(text) for text in texts]


def write_jsonl(output_dir: Path, file_name: str, rows: list[dict[str, object]]) -> None:
    path = output_dir / file_name
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    safe_value = f'"{value}"' if " " in value else value
    if not env_path.exists():
        env_path.write_text(f"{key}={safe_value}\n")
        return
    lines = env_path.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = f"{key}={safe_value}"
            break
    else:
        lines.append(f"{key}={safe_value}")
    env_path.write_text("\n".join(lines) + "\n")


@dataclass(frozen=True)
class BankingDemoBundle:
    demo_profile: dict[str, Any]
    customer_profiles: list[dict[str, Any]]
    deposit_accounts: list[dict[str, Any]]
    debit_cards: list[dict[str, Any]]
    card_authorisations: list[dict[str, Any]]
    card_risk_events: list[dict[str, Any]]
    card_support_interventions: list[dict[str, Any]]
    card_recovery_options: list[dict[str, Any]]
    support_cases: list[dict[str, Any]]
    service_statuses: list[dict[str, Any]]
    support_guidance_docs_text: list[dict[str, Any]]
    summary: dict[str, int]
    flagship_account_id: str
    flagship_card_id: str


def build_demo_bundle(config: BankingDemoConfig) -> BankingDemoBundle:
    base_now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    flagship_opened = base_now - timedelta(days=940)
    flagship_decline_time = base_now - timedelta(minutes=36)
    flagship_risk_time = base_now - timedelta(minutes=34)
    flagship_intervention_time = base_now - timedelta(minutes=31)
    flagship_intervention_expiry = base_now + timedelta(hours=23, minutes=24)

    flagship_customer_id = f"{config.customer_id_prefix}_001"
    flagship_account_id = "ACC_001"
    flagship_card_id = "CARD_001"
    flagship_keep_option = "KEEP_TEMPORARY_BLOCK"
    flagship_unfreeze_option = "UNFREEZE_AFTER_VERIFICATION"
    flagship_replace_option = "ORDER_REPLACEMENT_CARD"

    demo_profile = {
        "customer_id": flagship_customer_id,
        "profile_reference": f"{config.profile_reference_prefix}-001",
        "display_name": "Maya Chen",
        "salutation": "Ms.",
        "customer_segment": config.plus_segment,
        "support_plan": config.plus_plan,
        "preferred_language": config.language_code,
        "email": "maya.chen@example.com",
        "mobile_number_masked": "+•• ••• ••• 184",
        "postal_region_prefix": "A1",
        "service_permissions": {
            "secure_app_messaging": True,
            "instant_card_controls": True,
            "priority_support_routing": True,
        },
        "cache_group_id": "plus_en",
    }

    customer_profiles = [
        demo_profile,
        {
            "customer_id": f"{config.customer_id_prefix}_002",
            "profile_reference": f"{config.profile_reference_prefix}-002",
            "display_name": "Jordan Lee",
            "salutation": "Mr.",
            "customer_segment": config.plus_segment,
            "support_plan": config.plus_plan,
            "preferred_language": config.language_code,
            "email": "jordan.lee@example.com",
            "mobile_number_masked": "+•• ••• ••• 502",
            "postal_region_prefix": "B2",
            "service_permissions": {
                "secure_app_messaging": True,
                "instant_card_controls": True,
                "priority_support_routing": True,
            },
            "cache_group_id": "plus_en",
        },
        {
            "customer_id": f"{config.customer_id_prefix}_003",
            "profile_reference": f"{config.profile_reference_prefix}-003",
            "display_name": "Casey Alvarez",
            "salutation": "Mx.",
            "customer_segment": config.standard_segment,
            "support_plan": config.standard_plan,
            "preferred_language": config.language_code,
            "email": "casey.alvarez@example.com",
            "mobile_number_masked": "+•• ••• ••• 771",
            "postal_region_prefix": "C3",
            "service_permissions": {
                "secure_app_messaging": True,
                "instant_card_controls": True,
                "priority_support_routing": False,
            },
            "cache_group_id": "standard_en",
        },
    ]

    deposit_accounts = [
        {
            "account_id": flagship_account_id,
            "customer_id": flagship_customer_id,
            "account_nickname": "Plus everyday account",
            "routing_code_masked": "12••78",
            "account_number_masked": "••••4812",
            "currency": config.currency_code,
            "account_status": "active",
            "ledger_balance": 5821.44,
            "available_balance": 5421.44,
            "overdraft_available": 400.00,
            "opened_at": ts(flagship_opened),
        },
        {
            "account_id": "ACC_002",
            "customer_id": f"{config.customer_id_prefix}_002",
            "account_nickname": "Plus spending account",
            "routing_code_masked": "12••44",
            "account_number_masked": "••••6710",
            "currency": config.currency_code,
            "account_status": "active",
            "ledger_balance": 11420.03,
            "available_balance": 11020.03,
            "overdraft_available": 1000.00,
            "opened_at": ts(base_now - timedelta(days=1580)),
        },
        {
            "account_id": "ACC_003",
            "customer_id": f"{config.customer_id_prefix}_003",
            "account_nickname": "Everyday spending",
            "routing_code_masked": "12••89",
            "account_number_masked": "••••0246",
            "currency": config.currency_code,
            "account_status": "active",
            "ledger_balance": 1840.72,
            "available_balance": 1740.72,
            "overdraft_available": 100.00,
            "opened_at": ts(base_now - timedelta(days=610)),
        },
    ]

    debit_cards = [
        {
            "card_id": flagship_card_id,
            "account_id": flagship_account_id,
            "customer_id": flagship_customer_id,
            "card_reference": "DBCARD-001",
            "product_name": config.card_product_name,
            "card_last4": "4812",
            "card_status": "temporarily_blocked",
            "status_summary": f"A temporary block is active while {config.bank_name} checks unusual card activity.",
            "digital_wallet_status": "active",
            "contactless_enabled": False,
            "cash_withdrawal_enabled": True,
            "issued_at": ts(base_now - timedelta(days=380)),
        },
        {
            "card_id": "CARD_002",
            "account_id": "ACC_002",
            "customer_id": f"{config.customer_id_prefix}_002",
            "card_reference": "DBCARD-002",
            "product_name": config.card_product_name,
            "card_last4": "6710",
            "card_status": "active",
            "status_summary": "Card is active and ready to use.",
            "digital_wallet_status": "active",
            "contactless_enabled": True,
            "cash_withdrawal_enabled": True,
            "issued_at": ts(base_now - timedelta(days=214)),
        },
        {
            "card_id": "CARD_003",
            "account_id": "ACC_003",
            "customer_id": f"{config.customer_id_prefix}_003",
            "card_reference": "DBCARD-003",
            "product_name": config.card_product_name,
            "card_last4": "0246",
            "card_status": "active",
            "status_summary": "Card is active and ready to use.",
            "digital_wallet_status": "not_provisioned",
            "contactless_enabled": True,
            "cash_withdrawal_enabled": True,
            "issued_at": ts(base_now - timedelta(days=91)),
        },
    ]

    card_authorisations = [
        {
            "authorisation_id": "AUTH_001",
            "card_id": flagship_card_id,
            "account_id": flagship_account_id,
            "risk_event_id": "RISK_001",
            "merchant_name": "Harbor Tech Online",
            "merchant_category": "electronics",
            "merchant_city": "Lisbon",
            "merchant_country": "PT",
            "currency": config.currency_code,
            "amount": 742.50,
            "channel": "ecommerce",
            "authorisation_status": "declined",
            "decline_reason_customer": "We declined this transaction because it looked unusual and temporarily blocked the card.",
            "occurred_at": ts(flagship_decline_time),
        },
        {
            "authorisation_id": "AUTH_002",
            "card_id": "CARD_002",
            "account_id": "ACC_002",
            "risk_event_id": "RISK_002",
            "merchant_name": "Corner Books",
            "merchant_category": "books",
            "merchant_city": "Dublin",
            "merchant_country": "IE",
            "currency": config.currency_code,
            "amount": 24.99,
            "channel": "contactless",
            "authorisation_status": "approved",
            "decline_reason_customer": "",
            "occurred_at": ts(base_now - timedelta(days=1, hours=2)),
        },
    ]

    card_risk_events = [
        {
            "risk_event_id": "RISK_001",
            "customer_id": flagship_customer_id,
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "linked_authorisation_id": "AUTH_001",
            "event_type": "suspected_fraud",
            "event_status": "active_review",
            "risk_reason_code": "UNUSUAL_ECOMMERCE_PATTERN",
            "risk_summary": f"The declined purchase did not match the recent card pattern, so {config.bank_name} placed a temporary safeguard on the card.",
            "detected_at": ts(flagship_risk_time),
            "detection_source": "card_risk_monitoring",
            "card_action_taken": "temporary_card_block",
            "review_window": "Review can continue until the customer completes verification or chooses a replacement path.",
        },
        {
            "risk_event_id": "RISK_002",
            "customer_id": f"{config.customer_id_prefix}_002",
            "account_id": "ACC_002",
            "card_id": "CARD_002",
            "linked_authorisation_id": "AUTH_002",
            "event_type": "routine_screening",
            "event_status": "cleared",
            "risk_reason_code": "NO_ACTION_REQUIRED",
            "risk_summary": "Routine transaction screening cleared the payment with no card controls applied.",
            "detected_at": ts(base_now - timedelta(days=1, hours=2)),
            "detection_source": "card_risk_monitoring",
            "card_action_taken": "none",
            "review_window": "No follow-up is needed.",
        },
    ]

    card_support_interventions = [
        {
            "intervention_id": "INTV_001",
            "customer_id": flagship_customer_id,
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "risk_event_id": "RISK_001",
            "intervention_type": "temporary_card_block",
            "intervention_status": "active",
            "applied_at": ts(flagship_intervention_time),
            "expires_at": ts(flagship_intervention_expiry),
            "service_channel": config.secure_messaging_channel,
            "customer_message": f"{config.bank_name} has temporarily blocked card ending 4812 while we verify unusual activity.",
            "next_step_summary": "The customer can keep the block in place, unfreeze the card after verification, or request a replacement card.",
        },
    ]

    card_recovery_options = [
        {
            "option_id": "OPT_001",
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "risk_event_id": "RISK_001",
            "intervention_id": "INTV_001",
            "option_code": flagship_keep_option,
            "option_label": "Keep the temporary block",
            "option_type": "currently_applied",
            "eligibility_status": "eligible",
            "service_channel": config.secure_messaging_channel,
            "expected_outcome": "The card remains temporarily blocked while the customer waits for more support or does nothing further.",
            "customer_note": f"This is the safeguard {config.bank_name} has already applied after the unusual card activity.",
        },
        {
            "option_id": "OPT_002",
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "risk_event_id": "RISK_001",
            "intervention_id": "INTV_001",
            "option_code": flagship_unfreeze_option,
            "option_label": "Unfreeze after verification",
            "option_type": "alternative",
            "eligibility_status": "eligible",
            "service_channel": config.secure_messaging_channel,
            "expected_outcome": f"{config.bank_name} completes a customer-verification step and then removes the temporary block from the card in this demo.",
            "customer_note": "Use this if the transaction was genuine and the customer wants the current card restored.",
        },
        {
            "option_id": "OPT_003",
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "risk_event_id": "RISK_001",
            "intervention_id": "INTV_001",
            "option_code": flagship_replace_option,
            "option_label": "Order a replacement card",
            "option_type": "alternative",
            "eligibility_status": "eligible",
            "service_channel": config.secure_messaging_channel,
            "expected_outcome": f"{config.bank_name} keeps the block in place and starts a replacement-card journey for the affected debit card in this demo.",
            "customer_note": "Use this if the customer does not want the current card returned to service.",
        },
    ]

    support_cases = [
        {
            "support_case_id": "CASE_001",
            "customer_id": flagship_customer_id,
            "account_id": flagship_account_id,
            "card_id": flagship_card_id,
            "case_type": "card_security_follow_up",
            "status": "open",
            "opened_at": ts(base_now - timedelta(minutes=28)),
            "channel": "app_message",
            "summary": f"Customer asked {config.bank_name} to confirm why a card purchase was declined.",
            "latest_note": "Temporary card block confirmed. Customer can choose verification to unfreeze or order a replacement card.",
        },
        {
            "support_case_id": "CASE_002",
            "customer_id": f"{config.customer_id_prefix}_003",
            "account_id": "ACC_003",
            "card_id": "CARD_003",
            "case_type": "profile_support",
            "status": "resolved",
            "opened_at": ts(base_now - timedelta(days=7)),
            "channel": "phone",
            "summary": "Customer asked for confirmation of the email address on file.",
            "latest_note": "Resolved after read-only profile verification.",
        },
    ]

    service_statuses = [
        {
            "service_status_id": "SRV_001",
            "service_name": config.app_service_name,
            "incident_category": "digital_channel",
            "customer_scope": "broad_retail_customers",
            "current_status": "operating_normally",
            "started_at": ts(base_now - timedelta(hours=6)),
            "updated_at": ts(base_now - timedelta(minutes=6)),
            "next_update_due": None,
            "affected_capabilities": ["balance_view", "card_controls", "secure_messaging"],
            "public_message": f"{config.mobile_app_name} is operating normally for balances, card controls, and secure messages.",
        },
        {
            "service_status_id": "SRV_002",
            "service_name": config.payments_service_name,
            "incident_category": "payments",
            "customer_scope": "selected_outbound_payments",
            "current_status": "operating_normally",
            "started_at": ts(base_now - timedelta(hours=6)),
            "updated_at": ts(base_now - timedelta(minutes=5)),
            "next_update_due": None,
            "affected_capabilities": ["outbound_real_time_payments", "payment_confirmations"],
            "public_message": "Real-time payments are operating normally.",
        },
        {
            "service_status_id": "SRV_003",
            "service_name": config.phone_service_name,
            "incident_category": "service_channel",
            "customer_scope": "normal_service",
            "current_status": "operating_normally",
            "started_at": ts(base_now - timedelta(hours=12)),
            "updated_at": ts(base_now - timedelta(minutes=12)),
            "next_update_due": None,
            "affected_capabilities": ["voice_support"],
            "public_message": "Phone support is operating normally.",
        },
    ]

    support_guidance_docs_text = [
        {
            "doc_id": "DOC_001",
            "category": "profile",
            "title": "Customer profile basics",
            "content": (
                f"The {config.bank_name} support profile stores the customer profile reference, service segment, language, "
                "email address, masked mobile number, and a summary of available self-service permissions. "
                "In this demo the profile is read-only and can be used to confirm what details are already on file."
            ),
        },
        {
            "doc_id": "DOC_002",
            "category": "card_security",
            "title": "Suspicious card activity and temporary safeguards",
            "content": (
                f"If a card payment looks unusual, {config.bank_name} may decline the transaction and place a temporary safeguard on the card "
                "while the customer verifies recent activity. Without access to the live card and authorisation records, the assistant "
                "can explain the general process but cannot confirm what happened to a specific card."
            ),
        },
        {
            "doc_id": "DOC_003",
            "category": "card_controls",
            "title": f"How card controls work in {config.mobile_app_name}",
            "content": (
                f"In {config.mobile_app_name}, customers can review card controls, freeze a card, and unfreeze a card after verification when the card is eligible. "
                "The assistant should treat these as shared product capabilities unless the customer pivots to their own card records."
            ),
        },
        {
            "doc_id": "DOC_004",
            "category": "card_security",
            "title": "What the customer can do after a temporary card block",
            "content": (
                "After a temporary card block, the customer may keep the safeguard in place, complete verification to unfreeze the card, "
                "or ask for a replacement card. The assistant should separate the record-backed current card state from general support guidance."
            ),
        },
        {
            "doc_id": "DOC_005",
            "category": "support_routing",
            "title": f"Card issue support routing in {config.mobile_app_name}",
            "content": (
                f"Customers can message {config.bank_name} securely from {config.mobile_app_name} or online banking at any time, and the digital assistant "
                "is available 24 hours a day, 7 days a week for first-line help. If more help is needed, a specialist can continue the case "
                "during the normal reply window. "
                f"{config.plus_segment} customers may be routed toward priority support channels and appointment-style follow-up when appropriate. "
                f"{config.standard_segment} customers follow the standard app and phone support route. This is routing guidance, not a promise about outcomes."
            ),
        },
        {
            "doc_id": "DOC_006",
            "category": "app_messaging",
            "title": "Secure messaging expectations",
            "content": (
                "Secure in-app or online messages are appropriate for follow-up on card controls, replacement requests, and support-case updates. "
                "The assistant can explain the channel expectations and available next steps, but should avoid promising a specific fraud decision or reimbursement outcome."
            ),
        },
    ]

    summary = {
        "customer_profiles": len(customer_profiles),
        "deposit_accounts": len(deposit_accounts),
        "debit_cards": len(debit_cards),
        "card_authorisations": len(card_authorisations),
        "card_risk_events": len(card_risk_events),
        "card_support_interventions": len(card_support_interventions),
        "card_recovery_options": len(card_recovery_options),
        "support_cases": len(support_cases),
        "service_statuses": len(service_statuses),
        "support_guidance_docs": len(support_guidance_docs_text),
    }

    return BankingDemoBundle(
        demo_profile=demo_profile,
        customer_profiles=customer_profiles,
        deposit_accounts=deposit_accounts,
        debit_cards=debit_cards,
        card_authorisations=card_authorisations,
        card_risk_events=card_risk_events,
        card_support_interventions=card_support_interventions,
        card_recovery_options=card_recovery_options,
        support_cases=support_cases,
        service_statuses=service_statuses,
        support_guidance_docs_text=support_guidance_docs_text,
        summary=summary,
        flagship_account_id=flagship_account_id,
        flagship_card_id=flagship_card_id,
    )


def generate_demo_data(
    *,
    config: BankingDemoConfig,
    bundle: BankingDemoBundle,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    del seed
    resolved_output_dir = output_dir or (ROOT / "output" / config.domain_id)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating embeddings for {config.bank_name} support guidance documents...")
    embeddings = embed([doc["content"] for doc in bundle.support_guidance_docs_text])
    guidance_docs = [
        {**doc, "content_embedding": embedding}
        for doc, embedding in zip(bundle.support_guidance_docs_text, embeddings)
    ]

    write_jsonl(resolved_output_dir, "customer_profiles.jsonl", bundle.customer_profiles)
    write_jsonl(resolved_output_dir, "deposit_accounts.jsonl", bundle.deposit_accounts)
    write_jsonl(resolved_output_dir, "debit_cards.jsonl", bundle.debit_cards)
    write_jsonl(resolved_output_dir, "card_authorisations.jsonl", bundle.card_authorisations)
    write_jsonl(resolved_output_dir, "card_risk_events.jsonl", bundle.card_risk_events)
    write_jsonl(resolved_output_dir, "card_support_interventions.jsonl", bundle.card_support_interventions)
    write_jsonl(resolved_output_dir, "card_recovery_options.jsonl", bundle.card_recovery_options)
    write_jsonl(resolved_output_dir, "support_cases.jsonl", bundle.support_cases)
    write_jsonl(resolved_output_dir, "service_statuses.jsonl", bundle.service_statuses)
    write_jsonl(resolved_output_dir, "support_guidance_docs.jsonl", guidance_docs)

    env_updates = {
        "DEMO_USER_ID": bundle.demo_profile["customer_id"],
        "DEMO_USER_NAME": bundle.demo_profile["display_name"],
        "DEMO_USER_EMAIL": bundle.demo_profile["email"],
    }
    if update_env_file:
        for key, value in env_updates.items():
            update_env(key, value)

    return GeneratedDataset(
        output_dir=str(resolved_output_dir),
        env_updates=env_updates,
        summary=dict(bundle.summary),
    )
