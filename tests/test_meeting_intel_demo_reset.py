"""Statement construction for the meeting-intel demo-state reset."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_reset_module():
    path = ROOT / "domains" / "meeting-intel" / "rdi" / "reset_demo_state.py"
    spec = importlib.util.spec_from_file_location("mi_reset_demo_state", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_restore_statement_only_writes_when_the_row_differs() -> None:
    module = _load_reset_module()
    statement = module._restore_statement(
        "action_items", "action_id", ["action_id", "status", "text"]
    )

    assert statement.startswith("INSERT INTO action_items (action_id, status, text) VALUES (%s, %s, %s)")
    assert "ON CONFLICT (action_id) DO UPDATE SET status = EXCLUDED.status, text = EXCLUDED.text" in statement
    # Without this guard every reset would rewrite every row and flood RDI with CDC events.
    assert (
        "WHERE (action_items.status, action_items.text) "
        "IS DISTINCT FROM (EXCLUDED.status, EXCLUDED.text)" in statement
    )


def test_tables_are_ordered_parents_before_children() -> None:
    module = _load_reset_module()
    order = [table for table, _ in module.TABLES]

    for parent, child in [
        ("people", "meeting_participants"),
        ("projects", "meetings"),
        ("meetings", "transcripts"),
        ("meetings", "action_items"),
        ("projects", "project_dependencies"),
        ("meetings", "agendas"),
    ]:
        assert order.index(parent) < order.index(child), f"{parent} must precede {child}"


def test_every_table_declares_a_primary_key_column() -> None:
    module = _load_reset_module()
    schema = (
        ROOT / "domains" / "meeting-intel" / "rdi" / "source-db" / "scripts" / "00-schema.sql"
    ).read_text(encoding="utf-8")

    for table, pk in module.TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table} (" in schema
        assert f"{pk} TEXT PRIMARY KEY" in schema
