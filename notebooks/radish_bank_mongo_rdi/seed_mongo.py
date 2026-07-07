"""Seed local MongoDB with Radish Bank source data for the RDI workshop."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from pymongo import MongoClient, ReplaceOne

SCRIPT_DIR = Path(__file__).resolve().parent
NOTEBOOKS_DIR = SCRIPT_DIR.parent
ROOT = NOTEBOOKS_DIR.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.domain_loader import load_domain  # noqa: E402
from export_seed_inventory import (  # noqa: E402
    DEFAULT_INVENTORY_OUTPUT,
    build_inventory_markdown,
    write_inventory_file,
)

DOMAIN_ID = "radish-bank"
DEFAULT_MONGODB_URI = "mongodb://localhost:27017/?replicaSet=rs0"
DEFAULT_MONGODB_DATABASE = "radish_bank_workshop"


def load_workshop_env() -> None:
    root_env = ROOT / ".env"
    workshop_env = SCRIPT_DIR / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=False)
    if workshop_env.exists():
        load_dotenv(workshop_env, override=True)
    os.environ.setdefault("MONGODB_URI", DEFAULT_MONGODB_URI)
    os.environ.setdefault("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)
    os.environ.setdefault("DEMO_DOMAIN", DOMAIN_ID)


def run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_local_mongo(*, skip_docker: bool) -> None:
    if skip_docker:
        return

    compose_path = NOTEBOOKS_DIR / "mongo_local" / "docker-compose.yml"
    if not compose_path.exists():
        raise FileNotFoundError(f"Missing {compose_path}")
    if shutil.which("docker") is None:
        raise RuntimeError(
            "Docker is required to start the local MongoDB source. "
            "Install Docker or pass --skip-docker and set MONGODB_URI to an existing replica set."
        )

    run_command(["docker", "compose", "-f", str(compose_path), "up", "-d"])

    for _ in range(30):
        ping = subprocess.run(
            [
                "docker",
                "exec",
                "iris-workshop-mongo",
                "mongosh",
                "--quiet",
                "--eval",
                "db.adminCommand('ping').ok",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if ping.returncode == 0 and "1" in ping.stdout:
            break
        time.sleep(1)
    else:
        raise RuntimeError("MongoDB container did not become ready")

    rs_eval = """
try {
  rs.status().ok
} catch (e) {
  rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'localhost:27017'}]}).ok
}
"""
    run_command(
        [
            "docker",
            "exec",
            "iris-workshop-mongo",
            "mongosh",
            "--quiet",
            "--eval",
            rs_eval,
        ]
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def generate_radish_bank_data() -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], dict[str, int]]:
    run_command([sys.executable, str(ROOT / "scripts" / "generate_models.py"), "--domain", DOMAIN_ID])
    run_command([sys.executable, str(ROOT / "scripts" / "validate_domain.py"), "--domain", DOMAIN_ID])

    domain = load_domain(DOMAIN_ID)
    output_dir = ROOT / domain.manifest.output_dir
    generated = domain.generate_demo_data(output_dir=output_dir, update_env_file=False)

    records_by_collection: dict[str, list[dict[str, Any]]] = {}
    id_field_by_collection: dict[str, str] = {}
    for spec in domain.get_entity_specs():
        collection_name = Path(spec.file_name).stem
        records_by_collection[collection_name] = read_jsonl(output_dir / spec.file_name)
        id_field_by_collection[collection_name] = spec.id_field

    return records_by_collection, id_field_by_collection, generated.summary


def seed_mongo(
    *,
    mongo_uri: str,
    database_name: str,
    records_by_collection: dict[str, list[dict[str, Any]]],
    id_field_by_collection: dict[str, str],
) -> dict[str, int]:
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[database_name]
        counts: dict[str, int] = {}
        for collection_name, rows in records_by_collection.items():
            id_field = id_field_by_collection[collection_name]
            collection = db[collection_name]
            collection.delete_many({})
            collection.create_index(id_field, unique=True)
            if rows:
                ops = [ReplaceOne({id_field: row[id_field]}, row, upsert=True) for row in rows]
                collection.bulk_write(ops)
            counts[collection_name] = collection.count_documents({})
        return counts
    finally:
        client.close()


def mask_uri(uri: str) -> str:
    parsed = urlsplit(uri)
    if "@" not in parsed.netloc:
        return uri
    host_part = parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit((parsed.scheme, f"***:***@{host_part}", parsed.path, parsed.query, parsed.fragment))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", default=None, help="MongoDB connection string.")
    parser.add_argument("--database", default=None, help="MongoDB database name to replace.")
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Do not start the bundled local MongoDB container.",
    )
    parser.add_argument(
        "--inventory-output",
        default=str(DEFAULT_INVENTORY_OUTPUT),
        help="Markdown inventory path to write after seeding.",
    )
    parser.add_argument("--no-inventory", action="store_true", help="Do not write a Markdown seed inventory.")
    args = parser.parse_args()

    load_workshop_env()
    mongo_uri = args.mongo_uri or os.environ.get("MONGODB_URI", DEFAULT_MONGODB_URI)
    database_name = args.database or os.environ.get("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)

    ensure_local_mongo(skip_docker=args.skip_docker)
    records_by_collection, id_field_by_collection, generated_summary = generate_radish_bank_data()
    mongo_counts = seed_mongo(
        mongo_uri=mongo_uri,
        database_name=database_name,
        records_by_collection=records_by_collection,
        id_field_by_collection=id_field_by_collection,
    )

    print(f"Seeded MongoDB database: {database_name}")
    print(f"MongoDB source URI: {mask_uri(mongo_uri)}")
    print("Generated dataset:")
    print(json.dumps(generated_summary, indent=2, sort_keys=True))
    print("MongoDB collection counts:")
    print(json.dumps(mongo_counts, indent=2, sort_keys=True))

    if not args.no_inventory:
        inventory_output = Path(args.inventory_output).expanduser()
        if not inventory_output.is_absolute():
            inventory_output = ROOT / inventory_output
        markdown = build_inventory_markdown(
            records_by_collection,
            source_label="Radish Bank generator",
            database_name=database_name,
        )
        write_inventory_file(inventory_output, markdown)
        print(f"Wrote seed inventory: {inventory_output}")


if __name__ == "__main__":
    main()
