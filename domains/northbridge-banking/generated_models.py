"""Generated Context Surface models for the Northbridge Bank domain."""

from __future__ import annotations

from typing import Any

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class CustomerProfile(ContextModel):
    """CustomerProfile entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_customer_profile:{customer_id}"

    customer_id: str = ContextField(
        description="Public-safe demo customer identifier",
        is_key_component=True,
    )

    profile_reference: str = ContextField(
        description="Profile reference",
        index="tag",
        no_stem=True,
    )

    display_name: str = ContextField(
        description="Customer display name",
        index="text",
        weight=2.0,
    )

    salutation: str = ContextField(
        description="Customer salutation",
        index="tag",
    )

    customer_segment: str = ContextField(
        description="Customer support segment such as Plus or Standard",
        index="tag",
    )

    support_plan: str = ContextField(
        description="Customer support plan label",
        index="tag",
    )

    preferred_language: str = ContextField(
        description="Preferred service language",
        index="tag",
    )

    email: str = ContextField(
        description="Read-only email on file",
        index="text",
        weight=1.3,
        no_stem=True,
    )

    mobile_number_masked: str = ContextField(
        description="Masked mobile number on file",
        index="tag",
        no_stem=True,
    )

    postal_region_prefix: str = ContextField(
        description="Partial postal region used for verification",
        index="tag",
    )

    service_permissions: dict[str, bool] = ContextField(
        description="Available self-service permissions for the customer",
    )

    cache_group_id: str = ContextField(
        description="Semantic cache cohort identifier",
        index="tag",
        no_stem=True,
    )

    deposit_accounts: Any = ContextRelationship(
        description="Deposit accounts belonging to this customer",
        target="DepositAccount",
        source_field="customer_id",
    )

    support_cases: Any = ContextRelationship(
        description="Support cases opened for this customer",
        target="SupportCase",
        source_field="customer_id",
    )


class DepositAccount(ContextModel):
    """DepositAccount entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_deposit_account:{account_id}"

    account_id: str = ContextField(
        description="Unique deposit-account identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    account_nickname: str = ContextField(
        description="Customer-facing account nickname",
        index="text",
        weight=1.6,
    )

    routing_code_masked: str = ContextField(
        description="Masked routing identifier",
        index="tag",
        no_stem=True,
    )

    account_number_masked: str = ContextField(
        description="Masked account number",
        index="tag",
        no_stem=True,
    )

    currency: str = ContextField(
        description="Account currency",
        index="tag",
    )

    account_status: str = ContextField(
        description="Current account status",
        index="tag",
    )

    ledger_balance: float = ContextField(
        description="Current ledger balance",
    )

    available_balance: float = ContextField(
        description="Available balance",
    )

    overdraft_available: float = ContextField(
        description="Available overdraft amount",
    )

    opened_at: str = ContextField(
        description="Account opening timestamp",
    )

    customer: Any = ContextRelationship(
        description="Customer owning this account",
        target="CustomerProfile",
        source_field="customer_id",
    )

    debit_cards: Any = ContextRelationship(
        description="Debit cards attached to this account",
        target="DebitCard",
        source_field="account_id",
    )

    support_interventions: Any = ContextRelationship(
        description="Support interventions tied to this account",
        target="CardSupportIntervention",
        source_field="account_id",
    )

    support_cases: Any = ContextRelationship(
        description="Support cases tied to this account",
        target="SupportCase",
        source_field="account_id",
    )


class DebitCard(ContextModel):
    """DebitCard entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_debit_card:{card_id}"

    card_id: str = ContextField(
        description="Unique debit-card identifier",
        is_key_component=True,
    )

    account_id: str = ContextField(
        description="Parent account identifier",
        index="tag",
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    card_reference: str = ContextField(
        description="Public-safe internal card reference",
        index="tag",
        no_stem=True,
    )

    product_name: str = ContextField(
        description="Card product name",
        index="text",
        weight=1.4,
    )

    card_last4: str = ContextField(
        description="Last four digits of the card",
        index="tag",
        no_stem=True,
    )

    card_status: str = ContextField(
        description="Customer-visible card status",
        index="tag",
    )

    status_summary: str = ContextField(
        description="Plain-language explanation of the current card state",
        index="text",
    )

    digital_wallet_status: str = ContextField(
        description="Digital wallet provisioning status",
        index="tag",
    )

    contactless_enabled: bool = ContextField(
        description="Whether contactless use is enabled",
    )

    cash_withdrawal_enabled: bool = ContextField(
        description="Whether cash withdrawals are enabled",
    )

    issued_at: str = ContextField(
        description="Card issue timestamp",
    )

    account: Any = ContextRelationship(
        description="Account owning this card",
        target="DepositAccount",
        source_field="account_id",
    )

    authorisations: Any = ContextRelationship(
        description="Card authorisations raised against this card",
        target="CardAuthorisation",
        source_field="card_id",
    )

    support_interventions: Any = ContextRelationship(
        description="Support interventions tied to this card",
        target="CardSupportIntervention",
        source_field="card_id",
    )


class CardAuthorisation(ContextModel):
    """CardAuthorisation entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_card_authorisation:{authorisation_id}"

    authorisation_id: str = ContextField(
        description="Unique card authorisation identifier",
        is_key_component=True,
    )

    card_id: str = ContextField(
        description="Card identifier",
        index="tag",
    )

    account_id: str = ContextField(
        description="Account identifier",
        index="tag",
    )

    risk_event_id: str = ContextField(
        description="Linked risk event identifier",
        index="tag",
    )

    merchant_name: str = ContextField(
        description="Merchant name",
        index="text",
        weight=1.8,
    )

    merchant_category: str = ContextField(
        description="Merchant category",
        index="tag",
    )

    merchant_city: str = ContextField(
        description="Merchant city",
        index="text",
    )

    merchant_country: str = ContextField(
        description="Merchant country code",
        index="tag",
    )

    currency: str = ContextField(
        description="Authorisation currency",
        index="tag",
    )

    amount: float = ContextField(
        description="Authorisation amount",
    )

    channel: str = ContextField(
        description="Card-present, contactless, wallet, or ecommerce",
        index="tag",
    )

    authorisation_status: str = ContextField(
        description="Approved or declined state",
        index="tag",
    )

    decline_reason_customer: str = ContextField(
        description="Customer-facing decline explanation",
        index="text",
    )

    occurred_at: str = ContextField(
        description="Authorisation timestamp",
    )

    card: Any = ContextRelationship(
        description="Card used for this authorisation",
        target="DebitCard",
        source_field="card_id",
    )

    account: Any = ContextRelationship(
        description="Account used for this authorisation",
        target="DepositAccount",
        source_field="account_id",
    )

    risk_event: Any = ContextRelationship(
        description="Risk event linked to this authorisation",
        target="CardRiskEvent",
        source_field="risk_event_id",
    )


class CardRiskEvent(ContextModel):
    """CardRiskEvent entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_card_risk_event:{risk_event_id}"

    risk_event_id: str = ContextField(
        description="Unique card risk event identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    account_id: str = ContextField(
        description="Account identifier",
        index="tag",
    )

    card_id: str = ContextField(
        description="Card identifier",
        index="tag",
    )

    linked_authorisation_id: str = ContextField(
        description="Linked authorisation identifier",
        index="tag",
    )

    event_type: str = ContextField(
        description="Risk event type",
        index="tag",
    )

    event_status: str = ContextField(
        description="Risk review status",
        index="tag",
    )

    risk_reason_code: str = ContextField(
        description="Operational risk reason code",
        index="tag",
    )

    risk_summary: str = ContextField(
        description="Plain-language summary of why the event was raised",
        index="text",
    )

    detected_at: str = ContextField(
        description="Detection timestamp",
    )

    detection_source: str = ContextField(
        description="Channel or service that raised the event",
        index="tag",
    )

    card_action_taken: str = ContextField(
        description="Action already applied to the card",
        index="tag",
    )

    review_window: str = ContextField(
        description="Expected review or verification window",
        index="text",
    )

    account: Any = ContextRelationship(
        description="Account tied to this risk event",
        target="DepositAccount",
        source_field="account_id",
    )

    card: Any = ContextRelationship(
        description="Card tied to this risk event",
        target="DebitCard",
        source_field="card_id",
    )

    linked_authorisation: Any = ContextRelationship(
        description="Authorisation that triggered this risk event",
        target="CardAuthorisation",
        source_field="linked_authorisation_id",
    )

    support_interventions: Any = ContextRelationship(
        description="Support interventions currently tied to this risk event",
        target="CardSupportIntervention",
        source_field="risk_event_id",
    )


class CardSupportIntervention(ContextModel):
    """CardSupportIntervention entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_card_support_intervention:{intervention_id}"

    intervention_id: str = ContextField(
        description="Unique support intervention identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    account_id: str = ContextField(
        description="Account identifier",
        index="tag",
    )

    card_id: str = ContextField(
        description="Card identifier",
        index="tag",
    )

    risk_event_id: str = ContextField(
        description="Risk event identifier",
        index="tag",
    )

    intervention_type: str = ContextField(
        description="Type of intervention applied",
        index="tag",
    )

    intervention_status: str = ContextField(
        description="Current intervention status",
        index="tag",
    )

    applied_at: str = ContextField(
        description="When the intervention was applied",
    )

    expires_at: str | None = ContextField(
        description="When the temporary intervention expires if known",
    )

    service_channel: str = ContextField(
        description="Channel the customer can use next",
        index="tag",
    )

    customer_message: str = ContextField(
        description="Customer-facing explanation of the current safeguard",
        index="text",
    )

    next_step_summary: str = ContextField(
        description="Customer-facing summary of what can happen next",
        index="text",
    )

    account: Any = ContextRelationship(
        description="Account tied to this intervention",
        target="DepositAccount",
        source_field="account_id",
    )

    card: Any = ContextRelationship(
        description="Card tied to this intervention",
        target="DebitCard",
        source_field="card_id",
    )

    risk_event: Any = ContextRelationship(
        description="Risk event behind this intervention",
        target="CardRiskEvent",
        source_field="risk_event_id",
    )

    recovery_options: Any = ContextRelationship(
        description="Recovery options available for this intervention",
        target="CardRecoveryOption",
        source_field="intervention_id",
    )


class CardRecoveryOption(ContextModel):
    """CardRecoveryOption entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_card_recovery_option:{option_id}"

    option_id: str = ContextField(
        description="Unique recovery option identifier",
        is_key_component=True,
    )

    account_id: str = ContextField(
        description="Account identifier",
        index="tag",
    )

    card_id: str = ContextField(
        description="Card identifier",
        index="tag",
    )

    risk_event_id: str = ContextField(
        description="Risk event identifier",
        index="tag",
    )

    intervention_id: str = ContextField(
        description="Intervention identifier",
        index="tag",
    )

    option_code: str = ContextField(
        description="Stable recovery option code",
        index="tag",
        no_stem=True,
    )

    option_label: str = ContextField(
        description="Short customer-facing option label",
        index="text",
        weight=1.7,
    )

    option_type: str = ContextField(
        description="currently_applied or alternative",
        index="tag",
    )

    eligibility_status: str = ContextField(
        description="Eligibility state for this option",
        index="tag",
    )

    service_channel: str = ContextField(
        description="Preferred service channel for this option",
        index="tag",
    )

    expected_outcome: str = ContextField(
        description="What the option does for the card or account",
        index="text",
    )

    customer_note: str = ContextField(
        description="Short plain-language note about the option",
        index="text",
    )

    account: Any = ContextRelationship(
        description="Account tied to this recovery option",
        target="DepositAccount",
        source_field="account_id",
    )

    card: Any = ContextRelationship(
        description="Card tied to this recovery option",
        target="DebitCard",
        source_field="card_id",
    )

    intervention: Any = ContextRelationship(
        description="Intervention this recovery option belongs to",
        target="CardSupportIntervention",
        source_field="intervention_id",
    )

    risk_event: Any = ContextRelationship(
        description="Risk event tied to this option",
        target="CardRiskEvent",
        source_field="risk_event_id",
    )


class SupportCase(ContextModel):
    """SupportCase entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_support_case:{support_case_id}"

    support_case_id: str = ContextField(
        description="Unique support case identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    account_id: str = ContextField(
        description="Account identifier",
        index="tag",
    )

    card_id: str = ContextField(
        description="Card identifier",
        index="tag",
    )

    case_type: str = ContextField(
        description="Support case type",
        index="tag",
    )

    status: str = ContextField(
        description="Current support case status",
        index="tag",
    )

    opened_at: str = ContextField(
        description="Case creation timestamp",
    )

    channel: str = ContextField(
        description="Channel used to open the case",
        index="tag",
    )

    summary: str = ContextField(
        description="Short support summary",
        index="text",
    )

    latest_note: str = ContextField(
        description="Most recent customer-facing note",
        index="text",
    )

    customer: Any = ContextRelationship(
        description="Customer tied to this support case",
        target="CustomerProfile",
        source_field="customer_id",
    )

    account: Any = ContextRelationship(
        description="Account tied to this support case",
        target="DepositAccount",
        source_field="account_id",
    )

    card: Any = ContextRelationship(
        description="Card tied to this support case",
        target="DebitCard",
        source_field="card_id",
    )


class ServiceStatus(ContextModel):
    """ServiceStatus entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_service_status:{service_status_id}"

    service_status_id: str = ContextField(
        description="Unique service-status identifier",
        is_key_component=True,
    )

    service_name: str = ContextField(
        description="Stable shared service name",
        index="tag",
        no_stem=True,
    )

    incident_category: str = ContextField(
        description="Type of service issue",
        index="tag",
    )

    customer_scope: str = ContextField(
        description="Who is affected by the issue",
        index="tag",
    )

    current_status: str = ContextField(
        description="Current customer-visible status",
        index="tag",
    )

    started_at: str = ContextField(
        description="Incident start timestamp",
    )

    updated_at: str = ContextField(
        description="Most recent status update timestamp",
    )

    next_update_due: str | None = ContextField(
        description="When the next public update is expected",
    )

    affected_capabilities: list[str] = ContextField(
        description="Capabilities affected by the incident",
    )

    public_message: str = ContextField(
        description="Customer-facing service status message",
        index="text",
    )


class SupportGuidanceDoc(ContextModel):
    """SupportGuidanceDoc entity for the Northbridge Bank domain."""

    __redis_key_template__ = "northbridge_banking_support_guidance_doc:{doc_id}"

    doc_id: str = ContextField(
        description="Unique guidance document identifier",
        is_key_component=True,
    )

    category: str = ContextField(
        description="Guidance topic category",
        index="tag",
    )

    title: str = ContextField(
        description="Guidance title",
        index="text",
        weight=2.0,
    )

    content: str = ContextField(
        description="Guidance content",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Vector embedding for the document content",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
