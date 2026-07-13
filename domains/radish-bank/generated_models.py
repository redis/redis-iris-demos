"""Generated Context Surface models for the Radish Bank domain."""

from __future__ import annotations

from typing import Any

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class Customer(ContextModel):
    """Customer entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_customer:{customer_id}"

    customer_id: str = ContextField(
        description="Unique customer identifier; demo customer is always CUST001 (use full id in filters, never C001).",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Customer full name",
        index="text",
        weight=2.0,
    )

    segment: str = ContextField(
        description="Segment e.g. retail, mass_affluent",
        index="tag",
    )

    home_branch_id: str = ContextField(
        description="Preferred home branch id",
        index="tag",
    )

    home_branch: Any = ContextRelationship(
        description="Home branch profile",
        target="Branch",
        source_field="home_branch_id",
    )

    accounts: Any = ContextRelationship(
        description="Deposit accounts for this customer",
        target="Account",
        source_field="customer_id",
    )

    cards: Any = ContextRelationship(
        description="Cards for this customer",
        target="Card",
        source_field="customer_id",
    )

    holdings: Any = ContextRelationship(
        description="Product holdings",
        target="ProductHolding",
        source_field="customer_id",
    )

    service_requests: Any = ContextRelationship(
        description="Service request history",
        target="ServiceRequest",
        source_field="customer_id",
    )


class Account(ContextModel):
    """Account entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_account:{account_id}"

    account_id: str = ContextField(
        description="Account identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Owning customer",
        index="tag",
    )

    account_type: str = ContextField(
        description="savings or current",
        index="tag",
    )

    balance_sgd: float = ContextField(
        description="Balance in SGD",
        index="numeric",
        sortable=True,
    )

    status: str = ContextField(
        description="active or inactive",
        index="tag",
    )

    customer: Any = ContextRelationship(
        description="Account owner",
        target="Customer",
        source_field="customer_id",
    )


class Card(ContextModel):
    """Card entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_card:{card_id}"

    card_id: str = ContextField(
        description="Card identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Cardholder customer id",
        index="tag",
    )

    card_name: str = ContextField(
        description="Product name",
        index="text",
    )

    annual_fee_sgd: float = ContextField(
        description="Annual fee SGD",
        index="numeric",
        sortable=True,
    )

    status: str = ContextField(
        description="active or blocked",
        index="tag",
    )

    customer: Any = ContextRelationship(
        description="Cardholder",
        target="Customer",
        source_field="customer_id",
    )


class FixedDepositPlan(ContextModel):
    """FixedDepositPlan entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_fd_plan:{plan_id}"

    plan_id: str = ContextField(
        description="Primary key for get-by-id tools: exactly FD6 or FD12 in this demo. Do not use 1, 2, or positional labels; map user 'first/second option' to the plan_id from your prior list result.",
        is_key_component=True,
    )

    tenure_months: int = ContextField(
        description="Tenure in months",
        index="numeric",
        sortable=True,
    )

    rate_percent: float = ContextField(
        description="Annual rate percent",
        index="numeric",
        sortable=True,
    )

    min_deposit_sgd: int = ContextField(
        description="Minimum deposit SGD",
        index="numeric",
        sortable=True,
    )


class InsurancePlan(ContextModel):
    """InsurancePlan entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_insurance_plan:{plan_id}"

    plan_id: str = ContextField(
        description="Primary key for get-by-id tools: exactly INS_BASIC or INS_PLUS in this demo. Do not use numeric placeholders; use plan_id from list/filter tool results.",
        is_key_component=True,
    )

    plan_name: str = ContextField(
        description="Marketing name",
        index="text",
        weight=2.0,
    )

    annual_premium_sgd: int = ContextField(
        description="Annual premium SGD",
        index="numeric",
        sortable=True,
    )

    coverage_sgd: int = ContextField(
        description="Coverage amount SGD",
        index="numeric",
        sortable=True,
    )


class Branch(ContextModel):
    """Branch entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_branch:{branch_id}"

    branch_id: str = ContextField(
        description="Branch identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Branch display name",
        index="text",
        weight=2.0,
    )

    area: str = ContextField(
        description="Area or town",
        index="tag",
    )

    branch_type: str = ContextField(
        description="full_branch or auto_lobby",
        index="tag",
    )

    hours: Any = ContextRelationship(
        description="Published operating hours",
        target="BranchHours",
        source_field="branch_id",
    )


class BranchHours(ContextModel):
    """BranchHours entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_branch_hours:{branch_id}"

    branch_id: str = ContextField(
        description="Branch this row describes",
        is_key_component=True,
    )

    hours_summary: str = ContextField(
        description="Human-readable hours",
        index="text",
    )


class ProductHolding(ContextModel):
    """ProductHolding entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_holding:{holding_id}"

    holding_id: str = ContextField(
        description="Holding identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Owner customer id",
        index="tag",
    )

    product_type: str = ContextField(
        description="card, fixed_deposit, insurance",
        index="tag",
    )

    product_name: str = ContextField(
        description="Display name",
        index="text",
    )

    status: str = ContextField(
        description="active or closed",
        index="tag",
    )

    customer: Any = ContextRelationship(
        description="Holding owner",
        target="Customer",
        source_field="customer_id",
    )


class ServiceRequest(ContextModel):
    """ServiceRequest entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_service_request:{request_id}"

    request_id: str = ContextField(
        description="Request identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer id",
        index="tag",
    )

    request_type: str = ContextField(
        description="annual_card_fee_waiver, fixed_deposit, insurance",
        index="tag",
    )

    status: str = ContextField(
        description="approved, rejected, pending",
        index="tag",
    )

    created_at: str = ContextField(
        description="ISO timestamp",
        index="tag",
    )

    customer: Any = ContextRelationship(
        description="Requesting customer",
        target="Customer",
        source_field="customer_id",
    )


class BankDocument(ContextModel):
    """BankDocument entity for the Radish Bank domain."""

    __redis_key_template__ = "radish_bank_document:{document_id}"

    document_id: str = ContextField(
        description="Stable document id",
        is_key_component=True,
    )

    title: str = ContextField(
        description="Document title",
        index="text",
        weight=2.0,
    )

    category: str = ContextField(
        description="fd_faq, insurance_faq, fee_waiver, branch_guide",
        index="tag",
    )

    content: str = ContextField(
        description="Markdown body",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Embedding of content for vector search",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
