"""Postgres access for meeting-intel write tools. RDI is the only Redis writer."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "postgres",
}


def postgres_settings() -> dict[str, Any]:
    return {
        "host": os.getenv("MEETING_INTEL_PG_HOST") or os.getenv("POSTGRES_HOST") or DEFAULTS["host"],
        "port": int(os.getenv("MEETING_INTEL_PG_PORT") or os.getenv("POSTGRES_PORT") or DEFAULTS["port"]),
        "dbname": os.getenv("MEETING_INTEL_PG_DB") or os.getenv("POSTGRES_DB") or DEFAULTS["dbname"],
        "user": os.getenv("MEETING_INTEL_PG_USER") or os.getenv("POSTGRES_USER") or DEFAULTS["user"],
        "password": os.getenv("MEETING_INTEL_PG_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or DEFAULTS["password"],
    }


@contextmanager
def postgres_conn() -> Iterator[Any]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("psycopg is required for meeting-intel write tools") from exc
    cfg = postgres_settings()
    with psycopg.connect(**cfg, autocommit=True) as conn:
        yield conn


RDI_NOTE = (
    "Wrote to Postgres (system of record). RDI will copy this into Redis within seconds. "
    "Re-read through Context Retriever to confirm rather than assuming the key is already there."
)
