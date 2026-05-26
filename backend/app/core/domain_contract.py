from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, Sequence

from pydantic import BaseModel, Field

from backend.app.core.domain_schema import EntitySpec


class PromptCard(BaseModel):
    eyebrow: str
    title: str
    prompt: str


class UiConfig(BaseModel):
    show_platform_surface: bool = False
    show_live_updates: bool = False
    platform_surface_eyebrow: str = "Platform surface"
    platform_surface_title: str = "Available tools and data planes"
    platform_data_planes: list[str] = Field(default_factory=list)
    live_updates_eyebrow: str = "Live updates"
    live_updates_title: str = "Live update feed"


class ThemeConfig(BaseModel):
    bg: str
    bg_accent_a: str
    bg_accent_b: str
    panel: str
    panel_strong: str
    panel_elevated: str
    line: str
    line_strong: str
    text: str
    muted: str
    soft: str
    accent: str
    user: str


class BrandingConfig(BaseModel):
    app_name: str
    subtitle: str
    hero_title: str
    placeholder_text: str
    logo_path: str
    starter_prompts: list[PromptCard]
    theme: ThemeConfig
    ui: UiConfig = Field(default_factory=UiConfig)


class NamespaceConfig(BaseModel):
    redis_prefix: str
    dataset_meta_key: str
    checkpoint_prefix: str
    checkpoint_write_prefix: str
    redis_instance_name: str
    surface_name: str
    agent_name: str


class RagConfig(BaseModel):
    tool_name: str
    status_text: str
    generating_text: str
    index_name_contains: str
    vector_field: str
    return_fields: list[str]
    num_results: int = 3
    answer_system_prompt: str
    title_fields: list[str] = Field(default_factory=lambda: ["title", "headline", "document_id"])
    label_fields: list[str] = Field(default_factory=lambda: ["category", "ticker", "page_label", "company_id"])
    body_fields: list[str] = Field(default_factory=lambda: ["content", "summary", "description", "text"])


class IdentityConfig(BaseModel):
    tool_name: str = "get_current_user_profile"
    id_env_var: str = "DEMO_USER_ID"
    name_env_var: str = "DEMO_USER_NAME"
    email_env_var: str = "DEMO_USER_EMAIL"
    id_field: str = "user_id"
    default_id: str
    default_name: str
    default_email: str
    description: str


class SemanticCacheConfig(BaseModel):
    enabled: bool = False
    cache_name: str = ""
    distance_threshold: float = 0.12
    ttl_seconds: int = 1800


class InternalToolAccessControl(BaseModel):
    access_control_enabled: bool = False
    touched_entity_classes: list[str] = Field(default_factory=list)
    access_class_override: str | None = None


class DemoUserOption(BaseModel):
    id: str
    label: str
    subtitle: str | None = None
    cache_group_id: str | None = None


class DomainManifest(BaseModel):
    id: str
    version: str = "1"
    description: str
    generated_models_module: str
    generated_models_path: str
    output_dir: str
    branding: BrandingConfig
    namespace: NamespaceConfig
    rag: RagConfig
    identity: IdentityConfig
    semantic_cache: SemanticCacheConfig = Field(default_factory=SemanticCacheConfig)


class InternalToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}, "required": []})
    access_control: InternalToolAccessControl = Field(default_factory=InternalToolAccessControl)


class GeneratedDataset(BaseModel):
    output_dir: str
    env_updates: dict[str, str]
    summary: dict[str, int]


class DomainPack(Protocol):
    manifest: DomainManifest

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        ...

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        ...

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        ...

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        ...

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        ...

    def generate_demo_data(
        self,
        *,
        output_dir: Path,
        seed: int | None = None,
        update_env_file: bool = False,
    ) -> GeneratedDataset:
        ...

    def validate(self) -> list[str]:
        ...
