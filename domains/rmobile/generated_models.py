"""Generated Context Surface models for the R-Mobile domain."""

from __future__ import annotations

from typing import Any

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class Customer(ContextModel):
    """Customer entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_customer:{customer_id}"

    customer_id: str = ContextField(
        description="Unique customer / account identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Account holder full name",
        index="text",
        weight=2.0,
    )

    email: str = ContextField(
        description="Account email",
        index="text",
        weight=1.5,
        no_stem=True,
    )

    phone: str | None = ContextField(
        description="Contact phone number",
    )

    account_status: str = ContextField(
        description="Account status: active, suspended, closed",
        index="tag",
    )

    account_type: str = ContextField(
        description="Account type: individual, family",
        index="tag",
    )

    billing_address: str = ContextField(
        description="Billing address",
    )

    city: str = ContextField(
        description="City",
        index="tag",
    )

    state: str = ContextField(
        description="State",
        index="tag",
    )

    autopay_enabled: str = ContextField(
        description="Whether autopay is on: true, false",
        index="tag",
    )

    tenure_months: str = ContextField(
        description="Months as customer",
        index="tag",
    )

    account_created_at: str = ContextField(
        description="ISO timestamp of account creation",
    )

    lines: Any = ContextRelationship(
        description="Phone lines on this account",
        target="Line",
        source_field="customer_id",
    )

    bills: Any = ContextRelationship(
        description="Bills for this account",
        target="Bill",
        source_field="customer_id",
    )

    tickets: Any = ContextRelationship(
        description="Support tickets filed by this customer",
        target="SupportTicket",
        source_field="customer_id",
    )


class Line(ContextModel):
    """Line entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_line:{line_id}"

    line_id: str = ContextField(
        description="Unique line identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Account holder",
        index="tag",
    )

    phone_number: str = ContextField(
        description="Phone number for this line",
        index="tag",
    )

    nickname: str = ContextField(
        description="Friendly name for the line e.g. Jamie's iPhone",
        index="text",
    )

    plan_id: str = ContextField(
        description="Current plan on this line",
        index="tag",
    )

    device_id: str | None = ContextField(
        description="Device attached to this line",
        index="tag",
    )

    status: str = ContextField(
        description="Line status: active, suspended, ported_out",
        index="tag",
    )

    sim_type: str = ContextField(
        description="SIM type: esim, physical",
        index="tag",
    )

    data_used_gb: float = ContextField(
        description="Data used this billing cycle in GB",
        index="numeric",
        sortable=True,
    )

    data_limit_gb: str = ContextField(
        description="Data limit: unlimited or numeric GB",
        index="tag",
    )

    hotspot_used_gb: float = ContextField(
        description="Hotspot data used this cycle in GB",
        index="numeric",
    )

    hotspot_limit_gb: float = ContextField(
        description="Hotspot data cap in GB",
        index="numeric",
    )

    voice_minutes_used: str = ContextField(
        description="Voice minutes used this cycle",
        index="tag",
    )

    text_count: str = ContextField(
        description="Text messages sent this cycle",
        index="tag",
    )

    activated_at: str = ContextField(
        description="ISO timestamp when line was activated",
    )

    customer: Any = ContextRelationship(
        description="Account holder",
        target="Customer",
        source_field="customer_id",
    )

    plan: Any = ContextRelationship(
        description="Service plan on this line",
        target="Plan",
        source_field="plan_id",
    )

    device: Any = ContextRelationship(
        description="Device on this line",
        target="Device",
        source_field="device_id",
    )


class Plan(ContextModel):
    """Plan entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_plan:{plan_id}"

    plan_id: str = ContextField(
        description="Unique plan identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Plan display name",
        index="text",
        weight=2.0,
    )

    plan_type: str = ContextField(
        description="Plan type: postpaid, prepaid",
        index="tag",
    )

    tier: str = ContextField(
        description="Plan tier: essentials, standard, plus, next",
        index="tag",
    )

    monthly_cost: float = ContextField(
        description="Monthly cost per line in USD",
        index="numeric",
        sortable=True,
    )

    data_limit_gb: str = ContextField(
        description="Data limit: unlimited or numeric GB",
        index="tag",
    )

    premium_data_gb: str = ContextField(
        description="Premium / non-deprioritized data cap",
        index="tag",
    )

    hotspot_gb: float = ContextField(
        description="Mobile hotspot data included in GB",
        index="numeric",
    )

    includes_international: str = ContextField(
        description="International texting and data included: true, false",
        index="tag",
    )

    includes_streaming: str | None = ContextField(
        description="Included streaming perks",
    )

    five_g_access: str = ContextField(
        description="5G tier: standard, uc, full",
        index="tag",
    )

    description: str = ContextField(
        description="Plan description and key features",
        index="text",
    )


class Device(ContextModel):
    """Device entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_device:{device_id}"

    device_id: str = ContextField(
        description="Unique device identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Account holder",
        index="tag",
    )

    line_id: str = ContextField(
        description="Line this device is on",
        index="tag",
    )

    make: str = ContextField(
        description="Device manufacturer: Apple, Samsung, Google",
        index="tag",
    )

    model: str = ContextField(
        description="Device model name",
        index="text",
        weight=2.0,
    )

    storage_gb: str = ContextField(
        description="Storage capacity",
        index="tag",
    )

    color: str = ContextField(
        description="Device color",
        index="tag",
    )

    installment_total: float = ContextField(
        description="Original device price",
        index="numeric",
    )

    installment_paid: float = ContextField(
        description="Amount paid so far",
        index="numeric",
    )

    installment_remaining: float = ContextField(
        description="Remaining balance owed",
        index="numeric",
        sortable=True,
    )

    installment_monthly: float = ContextField(
        description="Monthly installment payment",
        index="numeric",
    )

    months_remaining: str = ContextField(
        description="Installment months remaining",
        index="tag",
    )

    trade_in_credit: float = ContextField(
        description="Monthly trade-in credit applied",
        index="numeric",
    )

    insurance_plan: str = ContextField(
        description="Insurance: none, protection360, basic",
        index="tag",
    )

    insurance_monthly: float = ContextField(
        description="Monthly insurance premium",
        index="numeric",
    )

    purchase_date: str = ContextField(
        description="ISO date device was purchased",
    )

    upgrade_eligible_date: str | None = ContextField(
        description="ISO date eligible for upgrade",
    )

    customer: Any = ContextRelationship(
        description="Account holder",
        target="Customer",
        source_field="customer_id",
    )

    line: Any = ContextRelationship(
        description="Line this device is on",
        target="Line",
        source_field="line_id",
    )


class Bill(ContextModel):
    """Bill entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_bill:{bill_id}"

    bill_id: str = ContextField(
        description="Unique bill identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Account holder",
        index="tag",
    )

    billing_period: str = ContextField(
        description="Billing period YYYY-MM",
        index="tag",
    )

    total_amount: float = ContextField(
        description="Total bill amount in USD",
        index="numeric",
        sortable=True,
    )

    previous_balance: float = ContextField(
        description="Carried-over balance from prior bill",
        index="numeric",
    )

    payments_received: float = ContextField(
        description="Payments applied this cycle",
        index="numeric",
    )

    new_charges: float = ContextField(
        description="New charges this cycle",
        index="numeric",
    )

    status: str = ContextField(
        description="Bill status: paid, unpaid, overdue, processing",
        index="tag",
    )

    due_date: str = ContextField(
        description="ISO date payment is due",
    )

    paid_date: str | None = ContextField(
        description="ISO date payment was received",
    )

    payment_method: str | None = ContextField(
        description="Payment method used",
        index="tag",
    )

    autopay: str = ContextField(
        description="Paid via autopay: true, false",
        index="tag",
    )

    customer: Any = ContextRelationship(
        description="Account holder",
        target="Customer",
        source_field="customer_id",
    )

    charges: Any = ContextRelationship(
        description="Line-item charges on this bill",
        target="BillCharge",
        source_field="bill_id",
    )


class BillCharge(ContextModel):
    """BillCharge entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_bill_charge:{charge_id}"

    charge_id: str = ContextField(
        description="Unique charge identifier",
        is_key_component=True,
    )

    bill_id: str = ContextField(
        description="Parent bill",
        index="tag",
    )

    line_id: str | None = ContextField(
        description="Line this charge applies to",
        index="tag",
    )

    category: str = ContextField(
        description="Charge category: plan, device_installment, insurance, taxes_fees, one_time, credit, international",
        index="tag",
    )

    description: str = ContextField(
        description="Human-readable charge description",
        index="text",
    )

    amount: float = ContextField(
        description="Charge amount in USD (negative for credits)",
        index="numeric",
        sortable=True,
    )

    is_recurring: str = ContextField(
        description="Recurring charge: true, false",
        index="tag",
    )

    bill: Any = ContextRelationship(
        description="Parent bill",
        target="Bill",
        source_field="bill_id",
    )


class SupportTicket(ContextModel):
    """SupportTicket entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_support_ticket:{ticket_id}"

    ticket_id: str = ContextField(
        description="Unique ticket identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer who filed the ticket",
        index="tag",
    )

    line_id: str | None = ContextField(
        description="Related phone line",
        index="tag",
    )

    category: str = ContextField(
        description="Category: billing, network, device, plan_change, international, account, other",
        index="tag",
    )

    status: str = ContextField(
        description="Status: open, in_progress, resolved, closed",
        index="tag",
    )

    created_at: str = ContextField(
        description="ISO timestamp when ticket was created",
    )

    resolved_at: str | None = ContextField(
        description="ISO timestamp when resolved",
    )

    summary: str = ContextField(
        description="Ticket summary",
        index="text",
    )

    resolution: str | None = ContextField(
        description="How it was resolved",
    )

    customer: Any = ContextRelationship(
        description="Customer who filed the ticket",
        target="Customer",
        source_field="customer_id",
    )


class PolicyDoc(ContextModel):
    """PolicyDoc entity for the R-Mobile domain."""

    __redis_key_template__ = "rmobile_policy_doc:{doc_id}"

    doc_id: str = ContextField(
        description="Unique document identifier",
        is_key_component=True,
    )

    title: str = ContextField(
        description="Policy document title",
        index="text",
        weight=2.0,
    )

    category: str = ContextField(
        description="Category: billing, devices, plans, network, international, insurance, account",
        index="tag",
    )

    content: str = ContextField(
        description="Full policy text",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Vector embedding of policy content",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
