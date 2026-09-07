"""Assert Redis key counts match Postgres row counts for meeting-intel."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.redis_connection import create_redis_client
from backend.app.settings import get_settings

_pg_path = Path(__file__).resolve().parents[1] / "postgres.py"
import importlib.util

_spec = importlib.util.spec_from_file_location("meeting_intel_postgres", _pg_path)
_pg = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_pg)
postgres_conn = _pg.postgres_conn
postgres_settings = _pg.postgres_settings

PREFIXES = {
    "projects": "project:",
    "people": "person:",
    "meetings": "meeting:",
    "meeting_participants": "participant:",
    "transcripts": "transcript:",
    "decisions": "decision:",
    "action_items": "action:",
    "risks": "risk:",
    "project_dependencies": "dependency:",
    "agendas": "agenda:",
}

META_KEY = "meeting-intel:meta:dataset"


def _count_keys(client, prefix: str) -> int:
    n = 0
    cursor = 0
    pattern = f"{prefix}*"
    while True:
        cursor, batch = client.scan(cursor=cursor, match=pattern, count=200)
        n += len(batch)
        if cursor == 0:
            break
    return n


def _pg_counts() -> dict[str, int]:
    with postgres_conn() as conn:
        with conn.cursor() as cur:
            out = {}
            for table in PREFIXES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                out[table] = int(cur.fetchone()[0])
    return out


def _cdc_latency_ms(client) -> float | None:
    action_id = "act-verify-latency"
    start = time.perf_counter()
    try:
        with postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO action_items (
                      action_id, meeting_id, project_id, owner_person_id, text, status,
                      due_date, created_at, updated_at, source_segment_id, visibility
                    ) VALUES (
                      %s, 'mtg-2026-09-04-platform', 'proj-platform', 'person-maya',
                      'verify latency probe', 'open', CURRENT_DATE, NOW(), NOW(), NULL, 'team'
                    )
                    ON CONFLICT (action_id) DO UPDATE SET updated_at = NOW(), text = EXCLUDED.text
                    """,
                    (action_id,),
                )
        deadline = time.time() + 30
        key = f"action:{action_id}"
        while time.time() < deadline:
            if client.exists(key):
                return (time.perf_counter() - start) * 1000
            time.sleep(0.25)
        return None
    finally:
        try:
            with postgres_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM action_items WHERE action_id = %s", (action_id,))
        except Exception:
            pass


def main() -> None:
    print("Postgres:", postgres_settings()["host"], postgres_settings()["port"])
    pg = _pg_counts()
    settings = get_settings()
    client = create_redis_client(settings)
    redis_counts = {table: _count_keys(client, prefix) for table, prefix in PREFIXES.items()}
    mismatches = []
    summary = {}
    print(f"{'table':24} {'postgres':>10} {'redis':>10}")
    for table, prefix in PREFIXES.items():
        left, right = pg[table], redis_counts[table]
        summary[table] = {"postgres": left, "redis": right, "prefix": prefix}
        mark = "OK" if left == right else "MISMATCH"
        print(f"{table:24} {left:10} {right:10}  {mark}")
        if left != right:
            mismatches.append(table)
    latency = _cdc_latency_ms(client)
    if latency is None:
        print("CDC probe: timed out after 30s (pipeline not streaming?)")
    else:
        print(f"CDC probe latency: {latency:.0f} ms (insert → Redis key)")
    client.execute_command("JSON.SET", META_KEY, "$", json.dumps({t: pg[t] for t in PREFIXES}))
    print(f"Wrote dataset summary → {META_KEY}")
    if mismatches:
        raise SystemExit(f"Count mismatch on: {', '.join(mismatches)}")
    print("mi-verify passed.")


if __name__ == "__main__":
    main()
