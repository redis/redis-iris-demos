"""Load generated JSONL data into the active domain's Context Surface."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from context_surfaces import UnifiedClient  # noqa: E402

from backend.app.core.domain_loader import load_domain  # noqa: E402
from backend.app.settings import get_settings  # noqa: E402


def load_records(*, output_dir: Path, entity_by_file: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    payloads: dict[str, list[dict[str, Any]]] = {}
    for file_name, entity in entity_by_file.items():
        path = output_dir / file_name
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        payloads[entity.class_name] = rows
    return payloads


def load_generated_models(module_name: str, module_path: str, class_names: list[str]) -> dict[str, type]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        resolved = ROOT / module_path
        spec = importlib.util.spec_from_file_location(
            module_name.replace(".", "_").replace("-", "_"),
            resolved,
        )
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return {class_name: getattr(module, class_name) for class_name in class_names}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()

    settings = get_settings()
    domain = load_domain(args.domain or settings.demo_domain)
    if getattr(domain.manifest, "data_plane", "jsonl") == "rdi":
        print(
            f"Domain '{domain.manifest.id}' uses the RDI data plane. "
            "Skipping JSONL import so RDI remains the only writer of Redis keys."
        )
        print("Apply Postgres seed + the RDI pipeline, then run make mi-verify.")
        print("Dataset metadata is written by make mi-verify after key counts match.")
        return
    admin_key = settings.ctx_admin_key
    surface_id = settings.ctx_surface_id

    if not admin_key:
        print("CTX_ADMIN_KEY is not set in .env")
        sys.exit(1)
    if not surface_id:
        print("CTX_SURFACE_ID is not set in .env. Run setup first.")
        sys.exit(1)

    entity_specs = domain.get_entity_specs()
    entity_by_file = {spec.file_name: spec for spec in entity_specs}
    class_names = [spec.class_name for spec in entity_specs]
    generated_models = load_generated_models(
        domain.manifest.generated_models_module,
        domain.manifest.generated_models_path,
        class_names,
    )
    output_dir = ROOT / domain.manifest.output_dir
    raw_records = load_records(output_dir=output_dir, entity_by_file=entity_by_file)

    batch_size = 25

    async with UnifiedClient() as client:
        for class_name, rows in raw_records.items():
            model_cls = generated_models[class_name]
            model_instances = [model_cls(**row) for row in rows]

            total_imported = 0
            total_failed = 0
            all_errors: list[Any] = []

            for i in range(0, len(model_instances), batch_size):
                batch = model_instances[i : i + batch_size]
                try:
                    result = await client.import_data(
                        admin_key=admin_key,
                        context_surface_id=surface_id,
                        records=batch,
                        on_conflict="overwrite",
                        on_error="fail_fast",
                    )
                    total_imported += result.imported
                    total_failed += result.failed
                    if result.errors:
                        all_errors.extend(result.errors)
                except Exception as exc:
                    batch_start = i + 1
                    batch_end = min(i + batch_size, len(model_instances))
                    print(f"  {class_name}: batch {batch_start}-{batch_end} FAILED: {exc}")
                    total_failed += len(batch)

            print(f"  {class_name}: imported={total_imported}, failed={total_failed}")
            for err in all_errors:
                print(f"    Error: {err}")

    summary = domain.write_dataset_meta(settings=settings, records=raw_records)
    print(f"  Wrote dataset summary → {domain.manifest.namespace.dataset_meta_key}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
