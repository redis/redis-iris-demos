from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BankingDemoConfig:
    """Branding and namespace inputs for a thin banking variant.

    The banking core owns the canonical entity names, semantic-cache contract,
    and flagship card-support flow. Variants configure naming, copy, routing
    labels, and seeded records without forking the underlying schema shape.
    """

    domain_id: str
    bank_name: str
    app_name: str
    mobile_app_name: str
    redis_prefix: str
    generated_models_module: str
    generated_models_path: str
    output_dir: str
    logo_path: str
    redis_instance_name: str
    surface_name: str
    agent_name: str
    plus_segment: str = "Plus"
    standard_segment: str = "Standard"
    plus_plan: str = "Plus Support"
    standard_plan: str = "Standard Support"
    currency_code: str = "USD"
    language_code: str = "EN"
    customer_id_prefix: str = "BANKCUST"
    profile_reference_prefix: str = "BANK-CP"
    card_product_name: str = "Bank Debit"
    app_service_name: str = "mobile_banking_app"
    payments_service_name: str = "real_time_payments"
    phone_service_name: str = "phone_support"

    @property
    def dataset_meta_key(self) -> str:
        return f"{self.redis_prefix}:meta:dataset"

    @property
    def checkpoint_prefix(self) -> str:
        return f"{self.redis_prefix}:checkpoint"

    @property
    def checkpoint_write_prefix(self) -> str:
        return f"{self.redis_prefix}:checkpoint_write"

    @property
    def semantic_cache_name(self) -> str:
        return f"{self.redis_prefix}_semantic_cache"

    @property
    def secure_messaging_channel(self) -> str:
        return f"{self.redis_prefix}_app_secure_messaging"
