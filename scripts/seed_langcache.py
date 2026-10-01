"""Seed LangCache with pre-filled entries for the active domain.

Reads entries from the domain's manifest.seed_langcache.

Usage:
    DOMAIN=reddash uv run python -m scripts.seed_langcache
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.domain_loader import get_active_domain
from backend.app.langcache_service import LangCacheService
from backend.app.settings import get_settings


def langcache_attributes_for_domain(domain_id: str, entry_attributes: dict[str, str]) -> dict[str, str]:
    return {
        **entry_attributes,
        "domain": domain_id,
    }


def should_flush_before_seed(raw_value: str | None = None) -> bool:
    value = os.getenv("LANGCACHE_FLUSH_BEFORE_SEED", "") if raw_value is None else raw_value
    return value.lower() in {"1", "true", "yes"}


async def main() -> None:
    settings = get_settings()
    domain = get_active_domain(settings)
    service = LangCacheService(settings)

    if not service.is_configured():
        print("LangCache not configured (skipping). Set LANGCACHE_HOST, LANGCACHE_CACHE_ID, LANGCACHE_API_KEY to enable.")
        return

    seeds = domain.manifest.seed_langcache
    if not seeds:
        print(f"Domain '{domain.manifest.id}' has no seed_langcache defined. Nothing to do.")
        return

    print(f"Domain: {domain.manifest.id}")
    if should_flush_before_seed():
        print("Flushing existing LangCache entries...")
        flushed = await service.flush()
        print(f"  {'OK' if flushed else 'FAILED (continuing anyway)'}")
    else:
        print("Leaving existing LangCache entries in place. Set LANGCACHE_FLUSH_BEFORE_SEED=1 to flush first.")

    print(f"Seeding {len(seeds)} entries...")
    for entry in seeds:
        ok = await service.store(
            prompt=entry.prompt,
            response=entry.response,
            attributes=langcache_attributes_for_domain(domain.manifest.id, entry.attributes),
        )
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {entry.prompt[:60]}")

    await service.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
