"""Generate demo data for a domain pack."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.domain_loader import load_domain
from backend.app.settings import ENV_PATH, get_settings
from scripts.setup_surface import upsert_env_values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    domain = load_domain(args.domain or settings.demo_domain)
    result = domain.generate_demo_data(
        output_dir=ROOT / domain.manifest.output_dir,
        seed=args.seed,
        update_env_file=True,
    )
    print(f"Generated data in {result.output_dir}")
    if result.env_updates:
        upsert_env_values(ENV_PATH, result.env_updates)
        print("Updated env values:")
        for key, value in result.env_updates.items():
            print(f"  {key}={value}")


if __name__ == "__main__":
    main()
