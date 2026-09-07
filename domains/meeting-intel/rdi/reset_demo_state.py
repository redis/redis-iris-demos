"""Undo demo-time writes with row-level SQL so RDI converges Redis back to seed state.

``mi-reset`` re-seeds with ``TRUNCATE`` and asks RDI to re-snapshot. Debezium does not
emit row deletes for ``TRUNCATE``, so keys the demo added (``act-cdc-live-overdue``,
``act-live-*``, the ``*-x-*`` rows from ``extract_from_transcript``) survive in Redis and
show up before the presenter runs the live CDC beat.

This script diffs Postgres against the generated seed and issues per-row ``DELETE`` and
``UPDATE`` statements instead. Every change travels the real path: Postgres → Debezium →
RDI → Redis. Nothing writes to Redis directly.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_sibling(name: str, relative: str) -> Any:
    path = Path(__file__).resolve().parents[1] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


postgres_conn = _load_sibling("meeting_intel_postgres", "postgres.py").postgres_conn
generate_demo_data = _load_sibling("meeting_intel_data_generator", "data_generator.py").generate_demo_data

# Parents first. Deletes walk this list in reverse so foreign keys stay satisfied.
TABLES: list[tuple[str, str]] = [
    ("people", "person_id"),
    ("projects", "project_id"),
    ("meetings", "meeting_id"),
    ("meeting_participants", "participant_id"),
    ("transcripts", "transcript_id"),
    ("decisions", "decision_id"),
    ("action_items", "action_id"),
    ("risks", "risk_id"),
    ("project_dependencies", "dependency_id"),
    ("agendas", "agenda_id"),
]


def _table_columns(cur: Any, table: str) -> list[str]:
    """Columns that actually exist in Postgres.

    The generated JSONL doubles as the Simple RAG corpus, so it carries fields such as
    ``summary_embedding`` that live only in Redis. Those are not columns here.
    """
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


def _canonical_rows(data_dir: Path, table: str) -> list[dict[str, Any]]:
    path = data_dir / f"{table}.jsonl"
    if not path.exists():
        raise SystemExit(f"Missing generated seed file {path}. Run: make mi-generate-seed")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _restore_statement(table: str, pk: str, columns: list[str]) -> str:
    """Upsert one seed row, writing only when the stored row actually differs.

    ``IS DISTINCT FROM`` runs the comparison in Postgres with real column types, so an
    unchanged row produces no UPDATE and therefore no CDC event. A reset after a clean
    run is close to a no-op instead of a full rewrite of every key.
    """
    others = [c for c in columns if c != pk]
    placeholders = ", ".join(["%s"] * len(columns))
    assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in others)
    stored = ", ".join(f"{table}.{c}" for c in others)
    incoming = ", ".join(f"EXCLUDED.{c}" for c in others)
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({pk}) DO UPDATE SET {assignments} "
        f"WHERE ({stored}) IS DISTINCT FROM ({incoming})"
    )


def reset(data_dir: Path, dry_run: bool = False) -> dict[str, dict[str, int]]:
    """Converge Postgres onto the seed. ``dry_run`` rolls back, so Debezium sees nothing."""
    summary: dict[str, dict[str, int]] = {}
    canonical = {table: _canonical_rows(data_dir, table) for table, _ in TABLES}

    with postgres_conn() as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                for table, pk in reversed(TABLES):
                    keep = [row[pk] for row in canonical[table]]
                    cur.execute(f"SELECT {pk} FROM {table} WHERE NOT ({pk} = ANY(%s))", (keep,))
                    extra = sorted(row[0] for row in cur.fetchall())
                    if extra:
                        cur.execute(f"DELETE FROM {table} WHERE {pk} = ANY(%s)", (extra,))
                        print(f"  {table}: removing {len(extra)} demo row(s): {', '.join(extra[:6])}")
                    summary.setdefault(table, {})["deleted"] = len(extra)

                for table, pk in TABLES:
                    rows = canonical[table]
                    summary.setdefault(table, {})["restored"] = 0
                    if not rows:
                        continue
                    existing = set(_table_columns(cur, table))
                    columns = [c for c in rows[0].keys() if c in existing]
                    cur.executemany(
                        _restore_statement(table, pk, columns),
                        [[row.get(column) for column in columns] for row in rows],
                    )
                    restored = max(cur.rowcount, 0)
                    summary[table]["restored"] = restored
                    if restored:
                        print(f"  {table}: restored {restored} row(s) to seed values")
        except Exception:
            conn.rollback()
            raise
        if dry_run:
            conn.rollback()
        else:
            conn.commit()

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without touching Postgres.",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Reuse output/meeting-intel/*.jsonl instead of regenerating the seed.",
    )
    args = parser.parse_args()

    data_dir = ROOT / "output" / "meeting-intel"
    if not args.skip_generate:
        generate_demo_data(output_dir=data_dir, update_env_file=False)

    print("Diffing Postgres against the generated seed...")
    summary = reset(data_dir, dry_run=args.dry_run)

    deleted = sum(counts.get("deleted", 0) for counts in summary.values())
    restored = sum(counts.get("restored", 0) for counts in summary.values())
    if args.dry_run:
        print(f"Dry run (rolled back): {deleted} row(s) would be deleted, {restored} restored.")
        return
    if not deleted and not restored:
        print("Already at seed state. Nothing to do.")
        return
    print(f"Deleted {deleted} demo row(s), restored {restored} row(s).")
    print("RDI is replaying these as CDC events; Redis converges within seconds.")
    print("Confirm: action:act-cdc-live-overdue should disappear from Redis Insight.")


if __name__ == "__main__":
    main()
