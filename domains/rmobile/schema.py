"""R-Mobile data-model definitions – single source of truth.

Each EntitySpec drives:
  • ContextModel code generation
  • Redis Search index creation
  • Sample-data generation
"""

from __future__ import annotations

from backend.app.core.domain_schema import (
    EntitySpec,
    FieldSpec,
    RelationshipSpec,
    entity_by_class,
    entity_by_file,
)


ENTITY_SPECS: tuple[EntitySpec, ...] = (
    # ── Customer ────────────────────────────────────────
    EntitySpec(
        class_name="Customer",
        redis_key_template="rmobile_customer:{customer_id}",
        file_name="customers.jsonl",
        id_field="customer_id",
        fields=(
            FieldSpec("customer_id", "str", "Unique customer / account identifier", is_key_component=True),
            FieldSpec("name", "str", "Account holder full name", index="text", weight=2.0),
            FieldSpec("email", "str", "Account email", index="text", weight=1.5, no_stem=True),
            FieldSpec("phone", "str | None", "Contact phone number"),
            FieldSpec("account_status", "str", "Account status: active, suspended, closed", index="tag"),
            FieldSpec("account_type", "str", "Account type: individual, family", index="tag"),
            FieldSpec("billing_address", "str", "Billing address"),
            FieldSpec("city", "str", "City", index="tag"),
            FieldSpec("state", "str", "State", index="tag"),
            FieldSpec("autopay_enabled", "str", "Whether autopay is on: true, false", index="tag"),
            FieldSpec("tenure_months", "str", "Months as customer", index="tag"),
            FieldSpec("account_created_at", "str", "ISO timestamp of account creation"),
        ),
        relationships=(
            RelationshipSpec("lines", "Phone lines on this account", "customer_id", "list[Line]"),
            RelationshipSpec("bills", "Bills for this account", "customer_id", "list[Bill]"),
            RelationshipSpec("tickets", "Support tickets filed by this customer", "customer_id", "list[SupportTicket]"),
        ),
    ),
    # ── Line ────────────────────────────────────────────
    EntitySpec(
        class_name="Line",
        redis_key_template="rmobile_line:{line_id}",
        file_name="lines.jsonl",
        id_field="line_id",
        fields=(
            FieldSpec("line_id", "str", "Unique line identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Account holder", index="tag"),
            FieldSpec("phone_number", "str", "Phone number for this line", index="tag"),
            FieldSpec("nickname", "str", "Friendly name for the line e.g. Jamie's iPhone", index="text"),
            FieldSpec("plan_id", "str", "Current plan on this line", index="tag"),
            FieldSpec("device_id", "str | None", "Device attached to this line", index="tag"),
            FieldSpec("status", "str", "Line status: active, suspended, ported_out", index="tag"),
            FieldSpec("sim_type", "str", "SIM type: esim, physical", index="tag"),
            FieldSpec("data_used_gb", "float", "Data used this billing cycle in GB", index="numeric", sortable=True),
            FieldSpec("data_limit_gb", "str", "Data limit: unlimited or numeric GB", index="tag"),
            FieldSpec("hotspot_used_gb", "float", "Hotspot data used this cycle in GB", index="numeric"),
            FieldSpec("hotspot_limit_gb", "float", "Hotspot data cap in GB", index="numeric"),
            FieldSpec("voice_minutes_used", "str", "Voice minutes used this cycle", index="tag"),
            FieldSpec("text_count", "str", "Text messages sent this cycle", index="tag"),
            FieldSpec("activated_at", "str", "ISO timestamp when line was activated"),
        ),
        relationships=(
            RelationshipSpec("customer", "Account holder", "customer_id", "Customer"),
            RelationshipSpec("plan", "Service plan on this line", "plan_id", "Plan"),
            RelationshipSpec("device", "Device on this line", "device_id", "Device"),
        ),
    ),
    # ── Plan ────────────────────────────────────────────
    EntitySpec(
        class_name="Plan",
        redis_key_template="rmobile_plan:{plan_id}",
        file_name="plans.jsonl",
        id_field="plan_id",
        fields=(
            FieldSpec("plan_id", "str", "Unique plan identifier", is_key_component=True),
            FieldSpec("name", "str", "Plan display name", index="text", weight=2.0),
            FieldSpec("plan_type", "str", "Plan type: postpaid, prepaid", index="tag"),
            FieldSpec("tier", "str", "Plan tier: essentials, standard, plus, next", index="tag"),
            FieldSpec("monthly_cost", "float", "Monthly cost per line in USD", index="numeric", sortable=True),
            FieldSpec("data_limit_gb", "str", "Data limit: unlimited or numeric GB", index="tag"),
            FieldSpec("premium_data_gb", "str", "Premium / non-deprioritized data cap", index="tag"),
            FieldSpec("hotspot_gb", "float", "Mobile hotspot data included in GB", index="numeric"),
            FieldSpec("includes_international", "str", "International texting and data included: true, false", index="tag"),
            FieldSpec("includes_streaming", "str | None", "Included streaming perks"),
            FieldSpec("five_g_access", "str", "5G tier: standard, uc, full", index="tag"),
            FieldSpec("description", "str", "Plan description and key features", index="text"),
        ),
    ),
    # ── Device ──────────────────────────────────────────
    EntitySpec(
        class_name="Device",
        redis_key_template="rmobile_device:{device_id}",
        file_name="devices.jsonl",
        id_field="device_id",
        fields=(
            FieldSpec("device_id", "str", "Unique device identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Account holder", index="tag"),
            FieldSpec("line_id", "str", "Line this device is on", index="tag"),
            FieldSpec("make", "str", "Device manufacturer: Apple, Samsung, Google", index="tag"),
            FieldSpec("model", "str", "Device model name", index="text", weight=2.0),
            FieldSpec("storage_gb", "str", "Storage capacity", index="tag"),
            FieldSpec("color", "str", "Device color", index="tag"),
            FieldSpec("installment_total", "float", "Original device price", index="numeric"),
            FieldSpec("installment_paid", "float", "Amount paid so far", index="numeric"),
            FieldSpec("installment_remaining", "float", "Remaining balance owed", index="numeric", sortable=True),
            FieldSpec("installment_monthly", "float", "Monthly installment payment", index="numeric"),
            FieldSpec("months_remaining", "str", "Installment months remaining", index="tag"),
            FieldSpec("trade_in_credit", "float", "Monthly trade-in credit applied", index="numeric"),
            FieldSpec("insurance_plan", "str", "Insurance: none, protection360, basic", index="tag"),
            FieldSpec("insurance_monthly", "float", "Monthly insurance premium", index="numeric"),
            FieldSpec("purchase_date", "str", "ISO date device was purchased"),
            FieldSpec("upgrade_eligible_date", "str | None", "ISO date eligible for upgrade"),
        ),
        relationships=(
            RelationshipSpec("customer", "Account holder", "customer_id", "Customer"),
            RelationshipSpec("line", "Line this device is on", "line_id", "Line"),
        ),
    ),
    # ── Bill ────────────────────────────────────────────
    EntitySpec(
        class_name="Bill",
        redis_key_template="rmobile_bill:{bill_id}",
        file_name="bills.jsonl",
        id_field="bill_id",
        fields=(
            FieldSpec("bill_id", "str", "Unique bill identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Account holder", index="tag"),
            FieldSpec("billing_period", "str", "Billing period YYYY-MM", index="tag"),
            FieldSpec("total_amount", "float", "Total bill amount in USD", index="numeric", sortable=True),
            FieldSpec("previous_balance", "float", "Carried-over balance from prior bill", index="numeric"),
            FieldSpec("payments_received", "float", "Payments applied this cycle", index="numeric"),
            FieldSpec("new_charges", "float", "New charges this cycle", index="numeric"),
            FieldSpec("status", "str", "Bill status: paid, unpaid, overdue, processing", index="tag"),
            FieldSpec("due_date", "str", "ISO date payment is due"),
            FieldSpec("paid_date", "str | None", "ISO date payment was received"),
            FieldSpec("payment_method", "str | None", "Payment method used", index="tag"),
            FieldSpec("autopay", "str", "Paid via autopay: true, false", index="tag"),
        ),
        relationships=(
            RelationshipSpec("customer", "Account holder", "customer_id", "Customer"),
            RelationshipSpec("charges", "Line-item charges on this bill", "bill_id", "list[BillCharge]"),
        ),
    ),
    # ── BillCharge ──────────────────────────────────────
    EntitySpec(
        class_name="BillCharge",
        redis_key_template="rmobile_bill_charge:{charge_id}",
        file_name="bill_charges.jsonl",
        id_field="charge_id",
        fields=(
            FieldSpec("charge_id", "str", "Unique charge identifier", is_key_component=True),
            FieldSpec("bill_id", "str", "Parent bill", index="tag"),
            FieldSpec("line_id", "str | None", "Line this charge applies to", index="tag"),
            FieldSpec("category", "str", "Charge category: plan, device_installment, insurance, taxes_fees, one_time, credit, international", index="tag"),
            FieldSpec("description", "str", "Human-readable charge description", index="text"),
            FieldSpec("amount", "float", "Charge amount in USD (negative for credits)", index="numeric", sortable=True),
            FieldSpec("is_recurring", "str", "Recurring charge: true, false", index="tag"),
        ),
        relationships=(
            RelationshipSpec("bill", "Parent bill", "bill_id", "Bill"),
        ),
    ),
    # ── SupportTicket ───────────────────────────────────
    EntitySpec(
        class_name="SupportTicket",
        redis_key_template="rmobile_support_ticket:{ticket_id}",
        file_name="support_tickets.jsonl",
        id_field="ticket_id",
        fields=(
            FieldSpec("ticket_id", "str", "Unique ticket identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Customer who filed the ticket", index="tag"),
            FieldSpec("line_id", "str | None", "Related phone line", index="tag"),
            FieldSpec("category", "str", "Category: billing, network, device, plan_change, international, account, other", index="tag"),
            FieldSpec("status", "str", "Status: open, in_progress, resolved, closed", index="tag"),
            FieldSpec("created_at", "str", "ISO timestamp when ticket was created"),
            FieldSpec("resolved_at", "str | None", "ISO timestamp when resolved"),
            FieldSpec("summary", "str", "Ticket summary", index="text"),
            FieldSpec("resolution", "str | None", "How it was resolved"),
        ),
        relationships=(
            RelationshipSpec("customer", "Customer who filed the ticket", "customer_id", "Customer"),
        ),
    ),
    # ── PolicyDoc (RAG) ─────────────────────────────────
    EntitySpec(
        class_name="PolicyDoc",
        redis_key_template="rmobile_policy_doc:{doc_id}",
        file_name="policy_docs.jsonl",
        id_field="doc_id",
        fields=(
            FieldSpec("doc_id", "str", "Unique document identifier", is_key_component=True),
            FieldSpec("title", "str", "Policy document title", index="text", weight=2.0),
            FieldSpec("category", "str", "Category: billing, devices, plans, network, international, insurance, account", index="tag"),
            FieldSpec("content", "str", "Full policy text", index="text"),
            FieldSpec(
                "content_embedding", "list[float]", "Vector embedding of policy content",
                index="vector", vector_dim=1536, distance_metric="cosine",
            ),
        ),
    ),
)

ENTITY_BY_FILE = entity_by_file(ENTITY_SPECS)
ENTITY_BY_CLASS = entity_by_class(ENTITY_SPECS)
