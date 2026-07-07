"""Generate compact Radish Bank demo JSONL + embeddings for policy docs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import openai
from dotenv import load_dotenv

from backend.app.core.domain_contract import GeneratedDataset

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS_DIR = Path(__file__).resolve().parent / "docs"


def ts(dt: datetime) -> str:
    return dt.isoformat()


now = datetime.now(timezone.utc)


def days_ago(days: int) -> str:
    return ts(now - timedelta(days=days))


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    client = openai.OpenAI()
    response = client.embeddings.create(
        input=texts,
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return [item.embedding for item in response.data]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


DEMO_CUSTOMER_ID = "CUST001"


def generate_demo_data(
    *,
    output_dir: Path,
    seed: int | None = None,
    update_env_file: bool = True,
) -> GeneratedDataset:
    del seed
    output_dir.mkdir(parents=True, exist_ok=True)

    customers = [
        {
            "customer_id": DEMO_CUSTOMER_ID,
            "name": "Merv Kwok",
            "segment": "retail",
            "home_branch_id": "BR001",
        },
        {
            "customer_id": "CUST002",
            "name": "Aisha Rahman",
            "segment": "mass_affluent",
            "home_branch_id": "BR002",
        },
        {
            "customer_id": "CUST003",
            "name": "Priya Menon",
            "segment": "retail",
            "home_branch_id": "BR004",
        },
        {
            "customer_id": "CUST004",
            "name": "Marcus Lee",
            "segment": "retail",
            "home_branch_id": "BR005",
        },
        {
            "customer_id": "CUST005",
            "name": "Chen Wei",
            "segment": "retail",
            "home_branch_id": "BR006",
        },
    ]
    accounts = [
        {
            "account_id": "ACC001",
            "customer_id": DEMO_CUSTOMER_ID,
            "account_type": "savings",
            "balance_sgd": 56500.0,
            "status": "active",
        },
        {
            "account_id": "ACC002",
            "customer_id": DEMO_CUSTOMER_ID,
            "account_type": "current",
            "balance_sgd": 22200.0,
            "status": "active",
        },
        {
            "account_id": "ACC003",
            "customer_id": DEMO_CUSTOMER_ID,
            "account_type": "savings",
            "balance_sgd": 18450.75,
            "status": "active",
        },
        {
            "account_id": "ACC004",
            "customer_id": DEMO_CUSTOMER_ID,
            "account_type": "current",
            "balance_sgd": 1500.25,
            "status": "inactive",
        },
        {
            "account_id": "ACC005",
            "customer_id": "CUST002",
            "account_type": "savings",
            "balance_sgd": 128400.5,
            "status": "active",
        },
        {
            "account_id": "ACC006",
            "customer_id": "CUST002",
            "account_type": "current",
            "balance_sgd": 34200.0,
            "status": "active",
        },
        {
            "account_id": "ACC007",
            "customer_id": "CUST002",
            "account_type": "savings",
            "balance_sgd": 25000.0,
            "status": "active",
        },
        {
            "account_id": "ACC008",
            "customer_id": "CUST003",
            "account_type": "savings",
            "balance_sgd": 9200.0,
            "status": "active",
        },
        {
            "account_id": "ACC009",
            "customer_id": "CUST003",
            "account_type": "current",
            "balance_sgd": 440.25,
            "status": "active",
        },
        {
            "account_id": "ACC010",
            "customer_id": "CUST004",
            "account_type": "current",
            "balance_sgd": 77250.0,
            "status": "active",
        },
        {
            "account_id": "ACC011",
            "customer_id": "CUST004",
            "account_type": "savings",
            "balance_sgd": 31000.0,
            "status": "active",
        },
        {
            "account_id": "ACC012",
            "customer_id": "CUST005",
            "account_type": "savings",
            "balance_sgd": 15680.8,
            "status": "active",
        },
        {
            "account_id": "ACC013",
            "customer_id": "CUST005",
            "account_type": "current",
            "balance_sgd": 8820.3,
            "status": "active",
        },
    ]
    cards = [
        {
            "card_id": "CARD001",
            "customer_id": DEMO_CUSTOMER_ID,
            "card_name": "Radish Cashback Card",
            "annual_fee_sgd": 196.2,
            "status": "active",
        },
        {
            "card_id": "CARD002",
            "customer_id": DEMO_CUSTOMER_ID,
            "card_name": "Radish Travel Card",
            "annual_fee_sgd": 261.6,
            "status": "active",
        },
        {
            "card_id": "CARD003",
            "customer_id": DEMO_CUSTOMER_ID,
            "card_name": "Radish Debit Card",
            "annual_fee_sgd": 0.0,
            "status": "blocked",
        },
        {
            "card_id": "CARD004",
            "customer_id": "CUST002",
            "card_name": "Radish Infinite Rewards Card",
            "annual_fee_sgd": 392.4,
            "status": "active",
        },
        {
            "card_id": "CARD005",
            "customer_id": "CUST003",
            "card_name": "Radish Cashback Card",
            "annual_fee_sgd": 196.2,
            "status": "active",
        },
        {
            "card_id": "CARD006",
            "customer_id": "CUST004",
            "card_name": "Radish Business Debit Card",
            "annual_fee_sgd": 0.0,
            "status": "active",
        },
        {
            "card_id": "CARD007",
            "customer_id": "CUST005",
            "card_name": "Radish Everyday Card",
            "annual_fee_sgd": 128.0,
            "status": "active",
        },
    ]
    fd_plans = [
        {"plan_id": "FD6", "tenure_months": 6, "rate_percent": 2.8, "min_deposit_sgd": 1000},
        {"plan_id": "FD12", "tenure_months": 12, "rate_percent": 3.1, "min_deposit_sgd": 1000},
    ]
    ins_plans = [
        {
            "plan_id": "INS_BASIC",
            "plan_name": "Basic Accident Cover",
            "annual_premium_sgd": 120,
            "coverage_sgd": 50000,
        },
        {
            "plan_id": "INS_PLUS",
            "plan_name": "Plus Accident Cover",
            "annual_premium_sgd": 220,
            "coverage_sgd": 100000,
        },
    ]
    branches = [
        {
            "branch_id": "BR001",
            "name": "Radish Bank Tampines Branch",
            "area": "Tampines",
            "branch_type": "full_branch",
        },
        {
            "branch_id": "BR002",
            "name": "Radish Bank Raffles Place Branch",
            "area": "Raffles Place",
            "branch_type": "full_branch",
        },
        {
            "branch_id": "BR003",
            "name": "Radish Bank Bishan Auto-Lobby",
            "area": "Bishan",
            "branch_type": "auto_lobby",
        },
        {
            "branch_id": "BR004",
            "name": "Radish Bank Orchard Wealth Centre",
            "area": "Orchard",
            "branch_type": "full_branch",
        },
        {
            "branch_id": "BR005",
            "name": "Radish Bank Jurong East Branch",
            "area": "Jurong East",
            "branch_type": "full_branch",
        },
        {
            "branch_id": "BR006",
            "name": "Radish Bank Changi Airport Auto-Lobby",
            "area": "Changi Airport",
            "branch_type": "auto_lobby",
        },
    ]
    branch_hours = [
        {"branch_id": "BR001", "hours_summary": "Mon-Fri 10:00-16:00, Sat 10:00-12:00"},
        {"branch_id": "BR002", "hours_summary": "Mon-Fri 09:30-16:00"},
        {"branch_id": "BR003", "hours_summary": "Daily 06:00-23:00"},
        {"branch_id": "BR004", "hours_summary": "Mon-Fri 10:00-18:00, Sat 10:00-14:00"},
        {"branch_id": "BR005", "hours_summary": "Mon-Fri 09:30-16:30, Sat 10:00-13:00"},
        {"branch_id": "BR006", "hours_summary": "Daily 05:00-24:00"},
    ]
    # Deposit accounts (savings/current) live in Account only — not ProductHolding.
    # Holdings cover placed products: cards, FDs, insurance (FD/insurance added by demo tools).
    holdings = [
        {
            "holding_id": "HOLD001",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "card",
            "product_name": "Radish Cashback Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD002",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "card",
            "product_name": "Radish Travel Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD003",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "card",
            "product_name": "Radish Debit Card",
            "status": "closed",
        },
        {
            "holding_id": "HOLD004",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "fixed_deposit",
            "product_name": "12M Fixed Deposit - SGD 9,000",
            "status": "active",
        },
        {
            "holding_id": "HOLD005",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "fixed_deposit",
            "product_name": "6M Fixed Deposit - SGD 8,500",
            "status": "active",
        },
        {
            "holding_id": "HOLD006",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "fixed_deposit",
            "product_name": "6M Fixed Deposit - SGD 5,000 (matured)",
            "status": "closed",
        },
        {
            "holding_id": "HOLD007",
            "customer_id": DEMO_CUSTOMER_ID,
            "product_type": "insurance",
            "product_name": "Legacy Accident Cover",
            "status": "closed",
        },
        {
            "holding_id": "HOLD008",
            "customer_id": "CUST002",
            "product_type": "card",
            "product_name": "Radish Infinite Rewards Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD009",
            "customer_id": "CUST002",
            "product_type": "fixed_deposit",
            "product_name": "12M Fixed Deposit - SGD 9,500",
            "status": "active",
        },
        {
            "holding_id": "HOLD010",
            "customer_id": "CUST002",
            "product_type": "insurance",
            "product_name": "Plus Accident Cover",
            "status": "active",
        },
        {
            "holding_id": "HOLD011",
            "customer_id": "CUST003",
            "product_type": "card",
            "product_name": "Radish Cashback Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD012",
            "customer_id": "CUST003",
            "product_type": "insurance",
            "product_name": "Basic Accident Cover",
            "status": "active",
        },
        {
            "holding_id": "HOLD013",
            "customer_id": "CUST004",
            "product_type": "card",
            "product_name": "Radish Business Debit Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD014",
            "customer_id": "CUST004",
            "product_type": "fixed_deposit",
            "product_name": "6M Fixed Deposit - SGD 7,500",
            "status": "active",
        },
        {
            "holding_id": "HOLD015",
            "customer_id": "CUST005",
            "product_type": "card",
            "product_name": "Radish Everyday Card",
            "status": "active",
        },
        {
            "holding_id": "HOLD016",
            "customer_id": "CUST005",
            "product_type": "fixed_deposit",
            "product_name": "12M Fixed Deposit - SGD 9,800",
            "status": "active",
        },
    ]
    service_requests = [
        {
            "request_id": "REQ001",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "annual_card_fee_waiver",
            "status": "approved",
            "created_at": days_ago(400),
        },
        {
            "request_id": "REQ002",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(360),
        },
        {
            "request_id": "REQ003",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "insurance",
            "status": "approved",
            "created_at": days_ago(330),
        },
        {
            "request_id": "REQ004",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "annual_card_fee_waiver",
            "status": "rejected",
            "created_at": days_ago(240),
        },
        {
            "request_id": "REQ005",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(190),
        },
        {
            "request_id": "REQ006",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "insurance",
            "status": "pending",
            "created_at": days_ago(110),
        },
        {
            "request_id": "REQ007",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "annual_card_fee_waiver",
            "status": "pending",
            "created_at": days_ago(42),
        },
        {
            "request_id": "REQ008",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(18),
        },
        {
            "request_id": "REQ009",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "insurance",
            "status": "rejected",
            "created_at": days_ago(7),
        },
        {
            "request_id": "REQ010",
            "customer_id": DEMO_CUSTOMER_ID,
            "request_type": "fixed_deposit",
            "status": "pending",
            "created_at": days_ago(2),
        },
        {
            "request_id": "REQ011",
            "customer_id": "CUST002",
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(72),
        },
        {
            "request_id": "REQ012",
            "customer_id": "CUST002",
            "request_type": "insurance",
            "status": "approved",
            "created_at": days_ago(44),
        },
        {
            "request_id": "REQ013",
            "customer_id": "CUST003",
            "request_type": "annual_card_fee_waiver",
            "status": "approved",
            "created_at": days_ago(210),
        },
        {
            "request_id": "REQ014",
            "customer_id": "CUST003",
            "request_type": "insurance",
            "status": "approved",
            "created_at": days_ago(15),
        },
        {
            "request_id": "REQ015",
            "customer_id": "CUST004",
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(30),
        },
        {
            "request_id": "REQ016",
            "customer_id": "CUST004",
            "request_type": "annual_card_fee_waiver",
            "status": "pending",
            "created_at": days_ago(9),
        },
        {
            "request_id": "REQ017",
            "customer_id": "CUST005",
            "request_type": "fixed_deposit",
            "status": "approved",
            "created_at": days_ago(64),
        },
        {
            "request_id": "REQ018",
            "customer_id": "CUST005",
            "request_type": "insurance",
            "status": "rejected",
            "created_at": days_ago(21),
        },
    ]

    doc_specs = [
        ("DOC_FD_FAQ", "Radish Bank Fixed Deposit FAQ", "fd_faq", "fixed_deposit_faq.md"),
        ("DOC_INS_FAQ", "Radish Bank Accident Insurance FAQ", "insurance_faq", "accident_insurance_faq.md"),
        ("DOC_FEE_WAIVER", "Annual Card Fee Waiver Policy (Demo)", "fee_waiver", "annual_card_fee_waiver_policy.md"),
        ("DOC_BRANCH", "Branch Services Guide", "branch_guide", "branch_services_guide.md"),
    ]
    doc_rows: list[dict[str, object]] = []
    texts_for_embed: list[str] = []
    for doc_id, title, category, filename in doc_specs:
        body = (DOCS_DIR / filename).read_text(encoding="utf-8")
        texts_for_embed.append(f"{title}\n\n{body}")
        doc_rows.append(
            {
                "document_id": doc_id,
                "title": title,
                "category": category,
                "content": body,
                "content_embedding": [],  # filled after embed()
            }
        )
    vectors = embed(texts_for_embed)
    for row, vec in zip(doc_rows, vectors, strict=True):
        row["content_embedding"] = vec

    _write_jsonl(output_dir / "customers.jsonl", customers)
    _write_jsonl(output_dir / "accounts.jsonl", accounts)
    _write_jsonl(output_dir / "cards.jsonl", cards)
    _write_jsonl(output_dir / "fixed_deposit_plans.jsonl", fd_plans)
    _write_jsonl(output_dir / "insurance_plans.jsonl", ins_plans)
    _write_jsonl(output_dir / "branches.jsonl", branches)
    _write_jsonl(output_dir / "branch_hours.jsonl", branch_hours)
    _write_jsonl(output_dir / "product_holdings.jsonl", holdings)
    _write_jsonl(output_dir / "service_requests.jsonl", service_requests)
    _write_jsonl(output_dir / "bank_documents.jsonl", doc_rows)

    env_updates = {
        "DEMO_USER_ID": DEMO_CUSTOMER_ID,
        "DEMO_USER_NAME": "Merv Kwok",
        "DEMO_USER_EMAIL": "merv.kwok@example.com",
        "CTX_SURFACE_NAME": '"Radish Bank Context Surface"',
        "CTX_AGENT_NAME": '"Radish Bank Service Agent"',
        "REDIS_INSTANCE_NAME": '"Radish Bank Redis Cloud"',
    }
    if update_env_file:
        env_path = ROOT / ".env"
        if env_path.exists():
            raw_lines = env_path.read_text(encoding="utf-8").splitlines()
            key_map = {k: v for k, v in env_updates.items()}
            new_lines: list[str] = []
            seen: set[str] = set()
            for line in raw_lines:
                if "=" in line and not line.strip().startswith("#"):
                    key = line.split("=", 1)[0].strip()
                    if key in key_map:
                        new_lines.append(f"{key}={key_map[key]}")
                        seen.add(key)
                        continue
                new_lines.append(line)
            for key, value in key_map.items():
                if key not in seen:
                    new_lines.append(f"{key}={value}")
            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    summary = {
        "customers": len(customers),
        "accounts": len(accounts),
        "cards": len(cards),
        "fixed_deposit_plans": len(fd_plans),
        "insurance_plans": len(ins_plans),
        "branches": len(branches),
        "branch_hours": len(branch_hours),
        "product_holdings": len(holdings),
        "service_requests": len(service_requests),
        "bank_documents": len(doc_rows),
    }
    return GeneratedDataset(output_dir=str(output_dir), env_updates=env_updates, summary=summary)
