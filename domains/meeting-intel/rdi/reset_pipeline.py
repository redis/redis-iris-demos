"""Re-seed Postgres and ask RDI to reset so it re-snapshots."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_dg = Path(__file__).resolve().parents[1] / "data_generator.py"
_spec = importlib.util.spec_from_file_location("meeting_intel_data_generator", _dg)
_gen = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_gen)
generate_demo_data = _gen.generate_demo_data

_pg_path = Path(__file__).resolve().parents[1] / "postgres.py"
_ps = importlib.util.spec_from_file_location("meeting_intel_postgres", _pg_path)
_pg = importlib.util.module_from_spec(_ps)
assert _ps and _ps.loader
_ps.loader.exec_module(_pg)
postgres_conn = _pg.postgres_conn

SQL_DIR = Path(__file__).resolve().parent / "source-db" / "scripts"


def _apply_sql(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def _reset_rdi() -> None:
    api = (os.getenv("RDI_API_URL") or "http://127.0.0.1:8080").rstrip("/")
    token = os.getenv("RDI_API_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=60.0) as client:
        for url in (f"{api}/api/v1/pipelines/reset", f"{api}/pipelines/reset"):
            response = client.post(url, headers=headers, json={})
            if response.status_code < 400:
                print(f"RDI reset accepted via {url} ({response.status_code})")
                return
            last = response
        raise SystemExit(
            f"RDI reset failed. Last status {last.status_code}: {last.text[:400]}\n"
            "Set RDI_API_URL / RDI_API_TOKEN, or reset the pipeline from Redis Insight."
        )


def main() -> None:
    generate_demo_data(output_dir=ROOT / "output" / "meeting-intel", update_env_file=False)
    print("Applying schema + seed to Postgres...")
    _apply_sql(SQL_DIR / "00-schema.sql")
    _apply_sql(SQL_DIR / "01-seed.sql")
    print("Resetting RDI pipeline so it re-snapshots...")
    _reset_rdi()
    print("Reset requested. Run make mi-verify after snapshot completes.")


if __name__ == "__main__":
    main()
