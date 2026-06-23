from __future__ import annotations

from pathlib import Path

from backend.app.core.domain_contract import GeneratedDataset
from domains.banking_core.config import BankingDemoConfig
from domains.banking_core.data_generator import build_demo_bundle, generate_demo_data as generate_banking_demo_data

CONFIG = BankingDemoConfig(
    domain_id="northbridge-banking",
    bank_name="Northbridge Bank",
    app_name="Northbridge Bank",
    mobile_app_name="Northbridge app",
    redis_prefix="northbridge_banking",
    generated_models_module="domains.northbridge-banking.generated_models",
    generated_models_path="domains/northbridge-banking/generated_models.py",
    output_dir="output/northbridge-banking",
    logo_path="domains/northbridge-banking/assets/logo.svg",
    redis_instance_name="Northbridge Bank Redis Cloud",
    surface_name="Northbridge Banking Surface",
    agent_name="Northbridge Banking Agent",
    plus_segment="Plus",
    standard_segment="Standard",
    plus_plan="Plus Support",
    standard_plan="Standard Support",
    currency_code="USD",
    language_code="EN",
    customer_id_prefix="NBCUST",
    profile_reference_prefix="NB-CP",
    card_product_name="Northbridge Debit",
    app_service_name="northbridge_mobile_app",
    payments_service_name="real_time_payments",
    phone_service_name="phone_support",
)

BUNDLE = build_demo_bundle(CONFIG)

DEMO_PROFILE = BUNDLE.demo_profile
CUSTOMER_PROFILES = BUNDLE.customer_profiles
CARD_RECOVERY_OPTIONS = BUNDLE.card_recovery_options
DATASET_SUMMARY = BUNDLE.summary


def generate_demo_data(
    *,
    output_dir: Path,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    return generate_banking_demo_data(
        config=CONFIG,
        bundle=BUNDLE,
        output_dir=output_dir,
        seed=seed,
        update_env_file=update_env_file,
    )
