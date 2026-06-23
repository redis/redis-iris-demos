from __future__ import annotations

from typing import Any, Sequence

from domains.banking_core.prompt import build_system_prompt as build_banking_system_prompt


def build_system_prompt(
    *,
    mcp_tools: Sequence[dict[str, Any]],
    runtime_config: dict[str, Any] | None = None,
) -> str:
    del runtime_config
    return build_banking_system_prompt(
        mcp_tools=mcp_tools,
        bank_name="Northbridge Bank",
        mobile_app_name="Northbridge app",
        app_service_name="northbridge_mobile_app",
        payments_service_name="real_time_payments",
        plus_segment="Plus",
        standard_segment="Standard",
    )
