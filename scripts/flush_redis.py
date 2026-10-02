"""Flush Redis keys except Agent Memory and LangCache data.

The Memory API (memory:* keys) and LangCache (langcache:* keys) can store their
data and search indexes in the same Redis database as our demo data. Deleting
those keys breaks the services (LangCache then returns 424 "Cache database is
unavailable"), and they won't rebuild automatically.

This script deletes all keys EXCEPT memory:* and langcache:* prefixed ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.redis_connection import create_redis_client
from backend.app.settings import get_settings

PRESERVED_PREFIXES = ("memory:", "langcache:")


def main() -> None:
    settings = get_settings()
    r = create_redis_client(settings)

    cursor = 0
    deleted = 0
    preserved = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, count=500)
        if keys:
            to_delete = []
            for k in keys:
                name = k if isinstance(k, str) else k.decode()
                if name.startswith(PRESERVED_PREFIXES):
                    preserved += 1
                else:
                    to_delete.append(k)
            if to_delete:
                r.delete(*to_delete)
                deleted += len(to_delete)
        if cursor == 0:
            break

    print(f"Flushed Redis at {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
    print(f"  Deleted {deleted} keys, preserved {preserved} Agent Memory/LangCache keys")


if __name__ == "__main__":
    main()
