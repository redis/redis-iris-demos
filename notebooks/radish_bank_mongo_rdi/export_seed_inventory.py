"""Export a readable inventory of the Radish Bank MongoDB seed data."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

SCRIPT_DIR = Path(__file__).resolve().parent
NOTEBOOKS_DIR = SCRIPT_DIR.parent
ROOT = NOTEBOOKS_DIR.parent

DEFAULT_MONGODB_URI = "mongodb://localhost:27017/?replicaSet=rs0"
DEFAULT_MONGODB_DATABASE = "radish_bank_workshop"
DEFAULT_INVENTORY_OUTPUT = ROOT / "output" / "radish-bank" / "mongo_seed_inventory.md"

COLLECTION_FIELDS: dict[str, list[str]] = {
    "customers": ["customer_id", "name", "segment", "home_branch_id"],
    "accounts": ["account_id", "customer_id", "account_type", "balance_sgd", "status"],
    "cards": ["card_id", "customer_id", "card_name", "annual_fee_sgd", "status"],
    "product_holdings": ["holding_id", "customer_id", "product_type", "product_name", "status"],
    "service_requests": ["request_id", "customer_id", "request_type", "status", "created_at"],
    "fixed_deposit_plans": ["plan_id", "tenure_months", "rate_percent", "min_deposit_sgd"],
    "insurance_plans": ["plan_id", "plan_name", "annual_premium_sgd", "coverage_sgd"],
    "branches": ["branch_id", "name", "area", "branch_type"],
    "branch_hours": ["branch_id", "hours_summary"],
    "bank_documents": ["document_id", "title", "category"],
}


def load_workshop_env() -> None:
    root_env = ROOT / ".env"
    workshop_env = SCRIPT_DIR / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=False)
    if workshop_env.exists():
        load_dotenv(workshop_env, override=True)
    os.environ.setdefault("MONGODB_URI", DEFAULT_MONGODB_URI)
    os.environ.setdefault("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _project_record(record: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: record.get(field, "") for field in fields}


def read_inventory_from_jsonl(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    records_by_collection: dict[str, list[dict[str, Any]]] = {}
    for collection_name, fields in COLLECTION_FIELDS.items():
        path = output_dir / f"{collection_name}.jsonl"
        if not path.exists():
            records_by_collection[collection_name] = []
            continue
        records = [_project_record(row, fields) for row in _read_jsonl(path)]
        records_by_collection[collection_name] = sorted(records, key=lambda row: str(row.get(fields[0], "")))
    return records_by_collection


def read_inventory_from_mongo(*, mongo_uri: str, database_name: str) -> dict[str, list[dict[str, Any]]]:
    client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[database_name]
        records_by_collection: dict[str, list[dict[str, Any]]] = {}
        for collection_name, fields in COLLECTION_FIELDS.items():
            projection = {field: 1 for field in fields}
            projection["_id"] = 0
            records = list(db[collection_name].find({}, projection).sort(fields[0]))
            records_by_collection[collection_name] = [_project_record(row, fields) for row in records]
        return records_by_collection
    finally:
        client.close()


def _table_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text.replace("\n", " ").replace("|", "\\|")


def _markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_table_value(row.get(header, "")) for header in headers) + " |")
    return lines


def build_inventory_markdown(
    records_by_collection: dict[str, list[dict[str, Any]]],
    *,
    source_label: str,
    database_name: str,
) -> str:
    lines = [
        "# Radish Bank Mongo Seed Inventory",
        "",
        "This file is generated from the Radish Bank MongoDB workshop seed data.",
        "Do not hand edit it; regenerate it with the command in the workshop README.",
        "",
        f"- Source: {source_label}",
        f"- MongoDB database: `{database_name}`",
        f"- Canonical generator: `domains/radish-bank/data_generator.py`",
        "",
        "## Counts",
        "",
        "| collection | records |",
        "| --- | ---: |",
    ]
    for collection_name in COLLECTION_FIELDS:
        lines.append(f"| {collection_name} | {len(records_by_collection.get(collection_name, []))} |")

    for collection_name, fields in COLLECTION_FIELDS.items():
        records = records_by_collection.get(collection_name, [])
        lines.extend(["", f"## {collection_name}", ""])
        if records:
            lines.extend(_markdown_table(fields, records))
        else:
            lines.append("_No records found._")
    return "\n".join(lines) + "\n"


def write_inventory_file(path: Path, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def _path_arg(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("mongo", "jsonl"), default="mongo")
    parser.add_argument("--mongo-uri", default=None, help="MongoDB connection string when --source=mongo.")
    parser.add_argument("--database", default=None, help="MongoDB database name when --source=mongo.")
    parser.add_argument(
        "--jsonl-dir",
        default=str(ROOT / "output" / "radish-bank"),
        help="Generated JSONL directory when --source=jsonl.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_INVENTORY_OUTPUT),
        help="Markdown file to write.",
    )
    parser.add_argument("--stdout", action="store_true", help="Print markdown to stdout instead of writing a file.")
    args = parser.parse_args()

    load_workshop_env()
    database_name = args.database or os.environ.get("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)

    if args.source == "mongo":
        mongo_uri = args.mongo_uri or os.environ.get("MONGODB_URI", DEFAULT_MONGODB_URI)
        records = read_inventory_from_mongo(mongo_uri=mongo_uri, database_name=database_name)
        source_label = "live MongoDB"
    else:
        records = read_inventory_from_jsonl(_path_arg(args.jsonl_dir))
        source_label = "generated JSONL"

    markdown = build_inventory_markdown(records, source_label=source_label, database_name=database_name)
    if args.stdout:
        sys.stdout.write(markdown)
        return

    output_path = _path_arg(args.output)
    write_inventory_file(output_path, markdown)
    print(f"Wrote seed inventory: {output_path}")


if __name__ == "__main__":
    main()
