from __future__ import annotations

import asyncio
import json
from typing import Any

from backend.app.context_surface_service import (
    _sanitize_property_schema,
    _sanitize_tool_definition,
)
from backend.app.langgraph_agent import (
    _format_tool_validation_error,
    _make_mcp_tool,
    _strip_redis_key_prefixes,
)


def test_sanitize_property_schema_preserves_generic_array_semantics() -> None:
    sanitized = _sanitize_property_schema("tags", {"type": "array", "description": "Search tags"})

    assert sanitized["items"] == {}


def test_sanitize_property_schema_defaults_embedding_vectors_to_number_items() -> None:
    sanitized = _sanitize_property_schema(
        "content_embedding",
        {"type": "array", "description": "Vector embedding used for similarity search"},
    )

    assert sanitized["items"] == {"type": "number"}


def test_sanitize_tool_definition_recurses_into_nullable_array_variants() -> None:
    tool_def = {
        "name": "search_vectors",
        "inputSchema": {
            "type": "object",
            "properties": {
                "embedding": {
                    "anyOf": [
                        {"type": "array", "description": "Embedding vector"},
                        {"type": "null"},
                    ]
                }
            },
        },
    }

    sanitized = _sanitize_tool_definition(tool_def)
    embedding_schema = sanitized["inputSchema"]["properties"]["embedding"]["anyOf"][0]

    assert embedding_schema["items"] == {"type": "number"}


def test_sanitize_tool_definition_defaults_plain_vector_arrays() -> None:
    tool_def = {
        "name": "redis__search_policy_by_content_embedding_similarity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vector": {
                    "type": "array",
                    "description": "Vector used for similarity search",
                }
            },
            "required": ["vector"],
        },
    }

    sanitized = _sanitize_tool_definition(tool_def)
    vector_schema = sanitized["inputSchema"]["properties"]["vector"]

    assert vector_schema["items"] == {"type": "number"}


def test_strip_redis_key_prefixes_reaches_nested_values() -> None:
    args = {
        "tag_conditions": [{"field": "customer_id", "value": "radish_bank_customer:CUST001"}],
        "limit": 5,
    }

    assert _strip_redis_key_prefixes(args) == {
        "tag_conditions": [{"field": "customer_id", "value": "CUST001"}],
        "limit": 5,
    }


class _RecordingService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, args))
        return {"ok": True}


def test_mcp_tool_passes_nested_args_as_json_serializable_dicts() -> None:
    service = _RecordingService()
    tool = _make_mcp_tool(
        {
            "name": "filter_account",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tag_conditions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string", "enum": ["customer_id"]},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    },
                    "limit": {"type": "integer"},
                },
            },
        },
        service,  # type: ignore[arg-type]
    )

    result = asyncio.run(
        tool.ainvoke({"tag_conditions": [{"field": "customer_id", "value": "CUST001"}]})
    )

    assert json.loads(result) == {"ok": True}
    name, args = service.calls[0]
    assert name == "filter_account"
    assert args == {"tag_conditions": [{"field": "customer_id", "value": "CUST001"}]}
    json.dumps(args)


def test_mcp_tool_wrapper_returns_structured_json_for_validation_errors() -> None:
    tool = _make_mcp_tool(
        {
            "name": "filter_order_by_customer_id",
            "description": "Find all orders for a customer",
            "inputSchema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        },
        cs_service=object(),  # type: ignore[arg-type]
    )

    assert tool.handle_validation_error == _format_tool_validation_error

    payload = json.loads(_format_tool_validation_error(ValueError("missing required field: value")))

    assert payload["error"] == "Tool input validation failed."
    assert payload["type"] == "ValueError"
    assert payload["detail"] == "missing required field: value"
