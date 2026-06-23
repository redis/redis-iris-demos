from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Sequence

from backend.app.core.domain_contract import (
    BrandingConfig,
    DomainManifest,
    IdentityConfig,
    NamespaceConfig,
    PromptCard,
    RagConfig,
    SeedMemory,
    ThemeConfig,
)
from domains.banking_core.domain_base import BankingDomainResources, BankingSupportDomainBase


def _load_local_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(f"northbridge_banking_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load northbridge-banking module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")

BUNDLE = _data_generator.BUNDLE
CONFIG = _data_generator.CONFIG
generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS


class NorthbridgeBankingDomain(BankingSupportDomainBase):
    manifest = DomainManifest(
        id="northbridge-banking",
        description=(
            "Public-safe consumer banking demo focused on debit-card safeguards, support routing, "
            "and shared product guidance."
        ),
        generated_models_module="domains.northbridge-banking.generated_models",
        generated_models_path="domains/northbridge-banking/generated_models.py",
        output_dir="output/northbridge-banking",
        branding=BrandingConfig(
            app_name="Northbridge Bank",
            subtitle="Banking support assistant",
            hero_title="Northbridge Bank",
            placeholder_text="Ask about your account, card, or support options",
            logo_path="domains/northbridge-banking/assets/logo.svg",
            demo_steps=[
                "My card was declined. What happened?",
                "What help do I usually get if something looks wrong with my card?",
                "How do card controls work in the Northbridge app?",
                "Show me my current card status.",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Card Security",
                    title="Card declined",
                    prompt="My card was declined. What happened?",
                ),
                PromptCard(
                    eyebrow="Tier-Scoped Support",
                    title="Card issue help",
                    prompt="What help do I usually get if something looks wrong with my card?",
                ),
                PromptCard(
                    eyebrow="Tier-Scoped Support",
                    title="Normal card help",
                    prompt="What help do I normally get if something looks wrong with my card?",
                ),
                PromptCard(
                    eyebrow="Public Guidance",
                    title="Card controls",
                    prompt="How do card controls work in the Northbridge app?",
                ),
                PromptCard(
                    eyebrow="Public Guidance",
                    title="App card controls",
                    prompt="How do the card controls in the Northbridge app work?",
                ),
                PromptCard(
                    eyebrow="Card Controls",
                    title="Current card status",
                    prompt="Show me my current card status.",
                ),
            ],
            theme=ThemeConfig(
                bg="#f3f8fd",
                bg_accent_a="rgba(0, 119, 204, 0.12)",
                bg_accent_b="rgba(78, 188, 255, 0.12)",
                panel="rgba(255, 255, 255, 0.93)",
                panel_strong="rgba(255, 255, 255, 0.98)",
                panel_elevated="rgba(247, 251, 255, 0.98)",
                line="rgba(8, 36, 63, 0.08)",
                line_strong="rgba(8, 36, 63, 0.18)",
                text="#0c2f4f",
                muted="#607a95",
                soft="#35556f",
                accent="#1499e6",
                user="#dceefb",
                landing_bg="#F2F8FD",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix=CONFIG.redis_prefix,
            dataset_meta_key=CONFIG.dataset_meta_key,
            checkpoint_prefix=CONFIG.checkpoint_prefix,
            checkpoint_write_prefix=CONFIG.checkpoint_write_prefix,
            redis_instance_name=CONFIG.redis_instance_name,
            surface_name=CONFIG.surface_name,
            agent_name=CONFIG.agent_name,
        ),
        rag=RagConfig(
            tool_name="vector_search_support_guidance",
            status_text="Searching Northbridge support guidance…",
            generating_text="Preparing answer…",
            index_name_contains="support",
            vector_field="content_embedding",
            return_fields=["title", "category", "content"],
            num_results=3,
            answer_system_prompt=(
                "You are Northbridge Bank's digital assistant in Simple RAG mode. "
                "Answer only from the provided customer-profile and support-guidance documents. "
                "Start by summarizing the most relevant guidance from those documents in plain language. "
                "For card-security questions, explain the general support process when the documents support it, "
                "such as temporary safeguards, verification, replacement-card routing, or secure messaging expectations. "
                "Be explicit that in Simple RAG mode you cannot see the customer's live account, card, authorisation, or risk records, "
                "so you cannot confirm what happened to their specific card. "
                "Do not claim access to personal or operational records. "
                "If the documents do not contain the answer, say so plainly."
            ),
        ),
        identity=IdentityConfig(
            id_field="customer_id",
            default_id=BUNDLE.demo_profile["customer_id"],
            default_name=BUNDLE.demo_profile["display_name"],
            default_email=BUNDLE.demo_profile["email"],
            description=(
                "Returns the signed-in Northbridge customer context for self-service support, including customer ID, "
                "profile reference, customer segment, language, read-only contact details, and service-permission flags."
            ),
        ),
        seed_memories=[
            SeedMemory(
                text="Customer is a Plus banking support member who prefers concise card-security next steps",
                topics=["banking", "card_support", "preferences"],
            ),
            SeedMemory(
                text="Customer expects Northbridge app guidance before phone escalation when card controls are available",
                topics=["banking", "card_controls", "support_preferences"],
            ),
        ],
        seed_langcache=[],
    )

    def __init__(self) -> None:
        super().__init__(
            config=CONFIG,
            manifest=self.manifest,
            entity_specs=ENTITY_SPECS,
            resources=BankingDomainResources(
                bundle=BUNDLE,
                prompt_builder=build_system_prompt,
                generate_demo_data_fn=_generate_demo_data_with_config,
            ),
        )

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        del runtime_config
        return build_system_prompt(mcp_tools=mcp_tools)


def _generate_demo_data_with_config(
    *,
    config: object,
    bundle: object,
    output_dir: Path,
    seed: int | None = None,
    update_env_file: bool = False,
):
    del config, bundle
    return generate_demo_data(output_dir=output_dir, seed=seed, update_env_file=update_env_file)


DOMAIN = NorthbridgeBankingDomain()
