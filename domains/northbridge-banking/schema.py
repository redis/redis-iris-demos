from __future__ import annotations

from backend.app.core.domain_schema import EntitySpec
from domains.banking_core.schema import build_entity_specs

ENTITY_SPECS: tuple[EntitySpec, ...] = build_entity_specs(namespace_prefix="northbridge_banking")
