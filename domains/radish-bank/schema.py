"""Radish Bank domain — entity specs (single demo customer, compact model)."""

from __future__ import annotations

from backend.app.core.domain_schema import (
    EntitySpec,
    FieldSpec,
    RelationshipSpec,
    entity_by_class,
    entity_by_file,
)

ENTITY_SPECS: tuple[EntitySpec, ...] = (
    EntitySpec(
        class_name="Customer",
        redis_key_template="radish_bank_customer:{customer_id}",
        file_name="customers.jsonl",
        id_field="customer_id",
        fields=(
            FieldSpec(
                "customer_id",
                "str",
                "Unique customer identifier; demo customer is always CUST001 (use full id in filters, never C001).",
                is_key_component=True,
            ),
            FieldSpec("name", "str", "Customer full name", index="text", weight=2.0),
            FieldSpec("segment", "str", "Segment e.g. retail, mass_affluent", index="tag"),
            FieldSpec("home_branch_id", "str", "Preferred home branch id", index="tag"),
        ),
        relationships=(
            RelationshipSpec("home_branch", "Home branch profile", "home_branch_id", "Branch"),
            RelationshipSpec("accounts", "Deposit accounts for this customer", "customer_id", "list[Account]"),
            RelationshipSpec("cards", "Cards for this customer", "customer_id", "list[Card]"),
            RelationshipSpec("holdings", "Product holdings", "customer_id", "list[ProductHolding]"),
            RelationshipSpec("service_requests", "Service request history", "customer_id", "list[ServiceRequest]"),
        ),
    ),
    EntitySpec(
        class_name="Account",
        redis_key_template="radish_bank_account:{account_id}",
        file_name="accounts.jsonl",
        id_field="account_id",
        fields=(
            FieldSpec("account_id", "str", "Account identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Owning customer", index="tag"),
            FieldSpec("account_type", "str", "savings or current", index="tag"),
            FieldSpec("balance_sgd", "float", "Balance in SGD", index="numeric", sortable=True),
            FieldSpec("status", "str", "active or inactive", index="tag"),
        ),
        relationships=(RelationshipSpec("customer", "Account owner", "customer_id", "Customer"),),
    ),
    EntitySpec(
        class_name="Card",
        redis_key_template="radish_bank_card:{card_id}",
        file_name="cards.jsonl",
        id_field="card_id",
        fields=(
            FieldSpec("card_id", "str", "Card identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Cardholder customer id", index="tag"),
            FieldSpec("card_name", "str", "Product name", index="text"),
            FieldSpec("annual_fee_sgd", "float", "Annual fee SGD", index="numeric", sortable=True),
            FieldSpec("status", "str", "active or blocked", index="tag"),
        ),
        relationships=(RelationshipSpec("customer", "Cardholder", "customer_id", "Customer"),),
    ),
    EntitySpec(
        class_name="FixedDepositPlan",
        redis_key_template="radish_bank_fd_plan:{plan_id}",
        file_name="fixed_deposit_plans.jsonl",
        id_field="plan_id",
        fields=(
            FieldSpec(
                "plan_id",
                "str",
                "Primary key for get-by-id tools: exactly FD6 or FD12 in this demo. "
                "Do not use 1, 2, or positional labels; map user 'first/second option' to the plan_id from your prior list result.",
                is_key_component=True,
            ),
            FieldSpec("tenure_months", "int", "Tenure in months", index="numeric", sortable=True),
            FieldSpec("rate_percent", "float", "Annual rate percent", index="numeric", sortable=True),
            FieldSpec("min_deposit_sgd", "int", "Minimum deposit SGD", index="numeric", sortable=True),
        ),
    ),
    EntitySpec(
        class_name="InsurancePlan",
        redis_key_template="radish_bank_insurance_plan:{plan_id}",
        file_name="insurance_plans.jsonl",
        id_field="plan_id",
        fields=(
            FieldSpec(
                "plan_id",
                "str",
                "Primary key for get-by-id tools: exactly INS_BASIC or INS_PLUS in this demo. "
                "Do not use numeric placeholders; use plan_id from list/filter tool results.",
                is_key_component=True,
            ),
            FieldSpec("plan_name", "str", "Marketing name", index="text", weight=2.0),
            FieldSpec("annual_premium_sgd", "int", "Annual premium SGD", index="numeric", sortable=True),
            FieldSpec("coverage_sgd", "int", "Coverage amount SGD", index="numeric", sortable=True),
        ),
    ),
    EntitySpec(
        class_name="Branch",
        redis_key_template="radish_bank_branch:{branch_id}",
        file_name="branches.jsonl",
        id_field="branch_id",
        fields=(
            FieldSpec("branch_id", "str", "Branch identifier", is_key_component=True),
            FieldSpec("name", "str", "Branch display name", index="text", weight=2.0),
            FieldSpec("area", "str", "Area or town", index="tag"),
            FieldSpec("branch_type", "str", "full_branch or auto_lobby", index="tag"),
        ),
        relationships=(RelationshipSpec("hours", "Published operating hours", "branch_id", "BranchHours"),),
    ),
    EntitySpec(
        class_name="BranchHours",
        redis_key_template="radish_bank_branch_hours:{branch_id}",
        file_name="branch_hours.jsonl",
        id_field="branch_id",
        fields=(
            FieldSpec("branch_id", "str", "Branch this row describes", is_key_component=True),
            FieldSpec("hours_summary", "str", "Human-readable hours", index="text"),
        ),
    ),
    EntitySpec(
        class_name="ProductHolding",
        redis_key_template="radish_bank_holding:{holding_id}",
        file_name="product_holdings.jsonl",
        id_field="holding_id",
        fields=(
            FieldSpec("holding_id", "str", "Holding identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Owner customer id", index="tag"),
            FieldSpec("product_type", "str", "card, fixed_deposit, insurance", index="tag"),
            FieldSpec("product_name", "str", "Display name", index="text"),
            FieldSpec("status", "str", "active or closed", index="tag"),
        ),
        relationships=(RelationshipSpec("customer", "Holding owner", "customer_id", "Customer"),),
    ),
    EntitySpec(
        class_name="ServiceRequest",
        redis_key_template="radish_bank_service_request:{request_id}",
        file_name="service_requests.jsonl",
        id_field="request_id",
        fields=(
            FieldSpec("request_id", "str", "Request identifier", is_key_component=True),
            FieldSpec("customer_id", "str", "Customer id", index="tag"),
            FieldSpec("request_type", "str", "annual_card_fee_waiver, fixed_deposit, insurance", index="tag"),
            FieldSpec("status", "str", "approved, rejected, pending", index="tag"),
            FieldSpec("created_at", "str", "ISO timestamp", index="tag"),
        ),
        relationships=(RelationshipSpec("customer", "Requesting customer", "customer_id", "Customer"),),
    ),
    EntitySpec(
        class_name="BankDocument",
        redis_key_template="radish_bank_document:{document_id}",
        file_name="bank_documents.jsonl",
        id_field="document_id",
        fields=(
            FieldSpec("document_id", "str", "Stable document id", is_key_component=True),
            FieldSpec("title", "str", "Document title", index="text", weight=2.0),
            FieldSpec("category", "str", "fd_faq, insurance_faq, fee_waiver, branch_guide", index="tag"),
            FieldSpec("content", "str", "Markdown body", index="text"),
            FieldSpec(
                "content_embedding",
                "list[float]",
                "Embedding of content for vector search",
                index="vector",
                vector_dim=1536,
                distance_metric="cosine",
            ),
        ),
    ),
)

ENTITY_BY_FILE = entity_by_file(ENTITY_SPECS)
ENTITY_BY_CLASS = entity_by_class(ENTITY_SPECS)
