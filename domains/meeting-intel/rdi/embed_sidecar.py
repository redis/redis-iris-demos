"""Embedding sidecar: fill vector fields RDI does not own.

Existing domains in this repo embed client-side in data_generator.py. Context
Surfaces does not embed at index time. RDI writes the JSON document; this
process JSON.SETs only $.summary_embedding / $.text_embedding.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openai import OpenAI

from backend.app.redis_connection import create_redis_client
from backend.app.settings import get_settings

TARGETS = (
    ("meeting:*", "$.summary", "$.summary_embedding"),
    ("transcript:*", "$.text", "$.text_embedding"),
    ("decision:*", "$.text", "$.text_embedding"),
    ("risk:*", "$.text", "$.text_embedding"),
)


def _embed(client: OpenAI, model: str, text: str) -> list[float]:
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def _scan(r, pattern: str) -> list[str]:
    cursor, keys = 0, []
    while True:
        cursor, batch = r.scan(cursor=cursor, match=pattern, count=200)
        keys.extend(batch)
        if cursor == 0:
            break
    return keys


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required for the embedding sidecar.")
    r = create_redis_client(settings)
    oai = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_embedding_model
    dry = os.getenv("MI_EMBED_DRY_RUN") == "1"
    updated = 0
    for pattern, src_path, dest_path in TARGETS:
        for key in _scan(r, pattern):
            raw = r.execute_command("JSON.GET", key, src_path)
            if not raw:
                continue
            text = raw.decode() if isinstance(raw, bytes) else str(raw)
            text = text.strip().strip('"')
            if not text:
                continue
            existing = r.execute_command("JSON.GET", key, dest_path)
            if existing and existing not in ("[]", "null", "[]\n"):
                continue
            if dry:
                print(f"would embed {key}")
                continue
            vec = _embed(oai, model, text)
            r.execute_command("JSON.SET", key, dest_path, json.dumps(vec))
            updated += 1
            time.sleep(0.02)
    print(f"Updated {updated} embedding fields.")


if __name__ == "__main__":
    main()
