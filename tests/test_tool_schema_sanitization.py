from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.app.context_surface_service import (
    _sanitize_property_schema,
    _sanitize_tool_definition,
)
from backend.app.langgraph_agent import (
    _format_tool_validation_error,
    _make_mcp_tool,
    _pydantic_model_from_json_schema,
    _resolve_json_schema_variant,
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


def test_resolve_json_schema_variant_handles_nullable_composed_schema() -> None:
    resolved, nullable = _resolve_json_schema_variant(
        {
            "anyOf": [
                {"type": "array", "items": {"type": "integer"}},
                {"type": "null"},
            ]
        }
    )

    assert nullable is True
    assert resolved == {"type": "array", "items": {"type": "integer"}}


def test_pydantic_model_from_json_schema_supports_arrays_objects_and_nullable_variants() -> None:
    model = _pydantic_model_from_json_schema(
        "VectorSearchArgs",
        {
            "type": "object",
            "properties": {
                "embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Embedding vector",
                },
                "filters": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {
                                "ids": {
                                    "type": ["array", "null"],
                                    "items": {"type": "integer"},
                                }
                            },
                            "required": ["ids"],
                        },
                        {"type": "null"},
                    ],
                    "description": "Optional filter object",
                },
            },
            "required": ["embedding", "filters"],
        },
    )

    instance = model(embedding=[0.1, 0.2], filters={"ids": [1, 2, 3]})
    assert instance.embedding == [0.1, 0.2]
    assert instance.filters.ids == [1, 2, 3]

    nullable_instance = model(embedding=[0.1], filters=None)
    assert nullable_instance.filters is None

    with pytest.raises(ValidationError):
        model(embedding=["bad"], filters={"ids": [1]})

    with pytest.raises(ValidationError):
        model(embedding=[0.1])


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
