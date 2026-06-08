"""Generate sample data for the R-Mobile wireless carrier demo."""

from __future__ import annotations

import json
import os
import sys
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openai
from dotenv import load_dotenv

from backend.app.core.domain_contract import GeneratedDataset

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "output" / "rmobile"


def ts(dt: datetime) -> str:
    return dt.isoformat()


now = datetime.now(timezone.utc)


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    try:
        client = openai.OpenAI()
        resp = client.embeddings.create(
            input=texts, model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return [item.embedding for item in resp.data]
    except Exception:
        return [fake_embedding(text) for text in texts]


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOMERS (3)
# ═══════════════════════════════════════════════════════════════════════════

DEMO_USER_ID = "CUST_DEMO_001"

CUSTOMERS = [
    {
        "customer_id": DEMO_USER_ID, "name": "Jamie Torres", "email": "jamie.torres@example.com",
        "phone": "+1-555-0147", "account_status": "active", "account_type": "family",
        "billing_address": "1842 Maple Ridge Dr, Denver, CO 80220",
        "city": "Denver", "state": "CO", "autopay_enabled": "true",
        "tenure_months": "28", "account_created_at": ts(now - timedelta(days=850)),
    },
    {
        "customer_id": "CUST_002", "name": "Morgan Blake", "email": "morgan.blake@example.com",
        "phone": "+1-555-0238", "account_status": "active", "account_type": "individual",
        "billing_address": "405 Congress Ave, Austin, TX 78701",
        "city": "Austin", "state": "TX", "autopay_enabled": "false",
        "tenure_months": "6", "account_created_at": ts(now - timedelta(days=185)),
    },
    {
        "customer_id": "CUST_003", "name": "Avery Nakamura", "email": "avery.nakamura@example.com",
        "phone": "+1-555-0319", "account_status": "suspended", "account_type": "individual",
        "billing_address": "2100 Market St, San Francisco, CA 94114",
        "city": "San Francisco", "state": "CA", "autopay_enabled": "true",
        "tenure_months": "14", "account_created_at": ts(now - timedelta(days=430)),
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  PLANS (5)
# ═══════════════════════════════════════════════════════════════════════════

PLANS = [
    {
        "plan_id": "ESSENTIALS", "name": "Essentials", "plan_type": "postpaid",
        "tier": "essentials", "monthly_cost": 26.25, "data_limit_gb": "unlimited",
        "premium_data_gb": "50", "hotspot_gb": 5.0,
        "includes_international": "false", "includes_streaming": None,
        "five_g_access": "standard",
        "description": "Basic unlimited plan. 50 GB premium data, 5 GB hotspot, standard 5G. Taxes and fees included.",
    },
    {
        "plan_id": "GO5G", "name": "Go5G", "plan_type": "postpaid",
        "tier": "standard", "monthly_cost": 35.00, "data_limit_gb": "unlimited",
        "premium_data_gb": "100", "hotspot_gb": 15.0,
        "includes_international": "false", "includes_streaming": "Apple TV+ included",
        "five_g_access": "uc",
        "description": "100 GB premium data, 15 GB hotspot, 5G UC access. Apple TV+ included. Taxes and fees included.",
    },
    {
        "plan_id": "GO5G_PLUS", "name": "Go5G Plus", "plan_type": "postpaid",
        "tier": "plus", "monthly_cost": 45.00, "data_limit_gb": "unlimited",
        "premium_data_gb": "unlimited", "hotspot_gb": 50.0,
        "includes_international": "true",
        "includes_streaming": "Apple TV+, Netflix Standard with Ads included",
        "five_g_access": "uc",
        "description": "Unlimited premium data, 50 GB hotspot, 5G UC. International texting and data in 215+ countries. Netflix and Apple TV+ included.",
    },
    {
        "plan_id": "GO5G_NEXT", "name": "Go5G Next", "plan_type": "postpaid",
        "tier": "next", "monthly_cost": 50.00, "data_limit_gb": "unlimited",
        "premium_data_gb": "unlimited", "hotspot_gb": 100.0,
        "includes_international": "true",
        "includes_streaming": "Apple TV+, Netflix Standard, Hulu included",
        "five_g_access": "full",
        "description": "Top-tier plan. Unlimited premium data, 100 GB hotspot, full 5G access. International included. Netflix Standard, Apple TV+, and Hulu.",
    },
    {
        "plan_id": "PREPAID_10GB", "name": "Simply Prepaid 10 GB", "plan_type": "prepaid",
        "tier": "essentials", "monthly_cost": 25.00, "data_limit_gb": "10",
        "premium_data_gb": "10", "hotspot_gb": 0.0,
        "includes_international": "false", "includes_streaming": None,
        "five_g_access": "standard",
        "description": "Prepaid plan with 10 GB high-speed data. No hotspot. Standard 5G. No contract required.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  LINES (5 — 3 on demo account, 1 each for other customers)
# ═══════════════════════════════════════════════════════════════════════════

LINES = [
    {
        "line_id": "LINE_001", "customer_id": DEMO_USER_ID,
        "phone_number": "(720) 555-0147", "nickname": "Jamie's iPhone",
        "plan_id": "GO5G_PLUS", "device_id": "DEV_001",
        "status": "active", "sim_type": "esim",
        "data_used_gb": 38.7, "data_limit_gb": "unlimited",
        "hotspot_used_gb": 4.2, "hotspot_limit_gb": 50.0,
        "voice_minutes_used": "247", "text_count": "1892",
        "activated_at": ts(now - timedelta(days=850)),
    },
    {
        "line_id": "LINE_002", "customer_id": DEMO_USER_ID,
        "phone_number": "(720) 555-0283", "nickname": "Riley's iPhone",
        "plan_id": "GO5G_PLUS", "device_id": "DEV_002",
        "status": "active", "sim_type": "physical",
        "data_used_gb": 62.4, "data_limit_gb": "unlimited",
        "hotspot_used_gb": 31.8, "hotspot_limit_gb": 50.0,
        "voice_minutes_used": "89", "text_count": "4231",
        "activated_at": ts(now - timedelta(days=540)),
    },
    {
        "line_id": "LINE_003", "customer_id": DEMO_USER_ID,
        "phone_number": "(720) 555-0391", "nickname": "Pat's Galaxy",
        "plan_id": "GO5G_PLUS", "device_id": "DEV_003",
        "status": "active", "sim_type": "esim",
        "data_used_gb": 12.1, "data_limit_gb": "unlimited",
        "hotspot_used_gb": 0.3, "hotspot_limit_gb": 50.0,
        "voice_minutes_used": "412", "text_count": "876",
        "activated_at": ts(now - timedelta(days=380)),
    },
    {
        "line_id": "LINE_004", "customer_id": "CUST_002",
        "phone_number": "(512) 555-0402", "nickname": "Morgan's Pixel",
        "plan_id": "GO5G", "device_id": "DEV_004",
        "status": "active", "sim_type": "esim",
        "data_used_gb": 22.5, "data_limit_gb": "unlimited",
        "hotspot_used_gb": 8.1, "hotspot_limit_gb": 15.0,
        "voice_minutes_used": "156", "text_count": "2340",
        "activated_at": ts(now - timedelta(days=185)),
    },
    {
        "line_id": "LINE_005", "customer_id": "CUST_003",
        "phone_number": "(415) 555-0518", "nickname": "Avery's iPhone",
        "plan_id": "ESSENTIALS", "device_id": "DEV_005",
        "status": "suspended", "sim_type": "physical",
        "data_used_gb": 0.0, "data_limit_gb": "unlimited",
        "hotspot_used_gb": 0.0, "hotspot_limit_gb": 5.0,
        "voice_minutes_used": "0", "text_count": "0",
        "activated_at": ts(now - timedelta(days=430)),
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  DEVICES (5)
# ═══════════════════════════════════════════════════════════════════════════

DEVICES = [
    {
        "device_id": "DEV_001", "customer_id": DEMO_USER_ID, "line_id": "LINE_001",
        "make": "Apple", "model": "iPhone 16 Pro", "storage_gb": "256", "color": "Natural Titanium",
        "installment_total": 999.99, "installment_paid": 958.21, "installment_remaining": 3.47,
        "installment_monthly": 3.47, "months_remaining": "1",
        "trade_in_credit": 16.67, "insurance_plan": "protection360", "insurance_monthly": 18.00,
        "purchase_date": ts(now - timedelta(days=700)), "upgrade_eligible_date": ts(now + timedelta(days=32)),
    },
    {
        "device_id": "DEV_002", "customer_id": DEMO_USER_ID, "line_id": "LINE_002",
        "make": "Apple", "model": "iPhone 15", "storage_gb": "128", "color": "Blue",
        "installment_total": 829.99, "installment_paid": 330.00, "installment_remaining": 449.82,
        "installment_monthly": 24.99, "months_remaining": "18",
        "trade_in_credit": 0.0, "insurance_plan": "none", "insurance_monthly": 0.0,
        "purchase_date": ts(now - timedelta(days=180)), "upgrade_eligible_date": ts(now + timedelta(days=365)),
    },
    {
        "device_id": "DEV_003", "customer_id": DEMO_USER_ID, "line_id": "LINE_003",
        "make": "Samsung", "model": "Galaxy S24", "storage_gb": "256", "color": "Onyx Black",
        "installment_total": 799.99, "installment_paid": 799.99, "installment_remaining": 0.0,
        "installment_monthly": 0.0, "months_remaining": "0",
        "trade_in_credit": 0.0, "insurance_plan": "none", "insurance_monthly": 0.0,
        "purchase_date": ts(now - timedelta(days=380)), "upgrade_eligible_date": ts(now - timedelta(days=15)),
    },
    {
        "device_id": "DEV_004", "customer_id": "CUST_002", "line_id": "LINE_004",
        "make": "Google", "model": "Pixel 9 Pro", "storage_gb": "128", "color": "Porcelain",
        "installment_total": 899.00, "installment_paid": 224.75, "installment_remaining": 674.25,
        "installment_monthly": 37.46, "months_remaining": "18",
        "trade_in_credit": 12.50, "insurance_plan": "basic", "insurance_monthly": 9.00,
        "purchase_date": ts(now - timedelta(days=185)), "upgrade_eligible_date": ts(now + timedelta(days=365)),
    },
    {
        "device_id": "DEV_005", "customer_id": "CUST_003", "line_id": "LINE_005",
        "make": "Apple", "model": "iPhone 14", "storage_gb": "128", "color": "Midnight",
        "installment_total": 699.99, "installment_paid": 699.99, "installment_remaining": 0.0,
        "installment_monthly": 0.0, "months_remaining": "0",
        "trade_in_credit": 0.0, "insurance_plan": "none", "insurance_monthly": 0.0,
        "purchase_date": ts(now - timedelta(days=430)), "upgrade_eligible_date": ts(now - timedelta(days=60)),
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  BILLS (5 — 3 for demo user, 1 each for others)
# ═══════════════════════════════════════════════════════════════════════════

BILLS = [
    # Demo user — current bill (higher than usual)
    {
        "bill_id": "BILL_001", "customer_id": DEMO_USER_ID,
        "billing_period": "2026-05", "total_amount": 187.43,
        "previous_balance": 0.0, "payments_received": 0.0, "new_charges": 187.43,
        "status": "unpaid", "due_date": ts(now + timedelta(days=8)),
        "paid_date": None, "payment_method": None, "autopay": "true",
    },
    # Demo user — last month (normal)
    {
        "bill_id": "BILL_002", "customer_id": DEMO_USER_ID,
        "billing_period": "2026-04", "total_amount": 153.22,
        "previous_balance": 0.0, "payments_received": 153.22, "new_charges": 153.22,
        "status": "paid", "due_date": ts(now - timedelta(days=22)),
        "paid_date": ts(now - timedelta(days=24)), "payment_method": "visa_4242", "autopay": "true",
    },
    # Demo user — two months ago (normal)
    {
        "bill_id": "BILL_003", "customer_id": DEMO_USER_ID,
        "billing_period": "2026-03", "total_amount": 153.22,
        "previous_balance": 0.0, "payments_received": 153.22, "new_charges": 153.22,
        "status": "paid", "due_date": ts(now - timedelta(days=52)),
        "paid_date": ts(now - timedelta(days=54)), "payment_method": "visa_4242", "autopay": "true",
    },
    # Morgan — current
    {
        "bill_id": "BILL_004", "customer_id": "CUST_002",
        "billing_period": "2026-05", "total_amount": 81.46,
        "previous_balance": 0.0, "payments_received": 0.0, "new_charges": 81.46,
        "status": "unpaid", "due_date": ts(now + timedelta(days=12)),
        "paid_date": None, "payment_method": None, "autopay": "false",
    },
    # Avery — overdue (account suspended)
    {
        "bill_id": "BILL_005", "customer_id": "CUST_003",
        "billing_period": "2026-04", "total_amount": 42.64,
        "previous_balance": 16.38, "payments_received": 0.0, "new_charges": 26.26,
        "status": "overdue", "due_date": ts(now - timedelta(days=30)),
        "paid_date": None, "payment_method": None, "autopay": "true",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  BILL CHARGES — line items for demo user bills
# ═══════════════════════════════════════════════════════════════════════════

BILL_CHARGES = [
    # ── BILL_001 (May, current, $187.43) ──
    # Plan charges: 3 lines x $45 = $135, minus $25 autopay/paperless discount
    {"charge_id": "CHG_001", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "plan", "description": "Go5G Plus — Jamie's iPhone", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_002", "bill_id": "BILL_001", "line_id": "LINE_002", "category": "plan", "description": "Go5G Plus — Riley's iPhone", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_003", "bill_id": "BILL_001", "line_id": "LINE_003", "category": "plan", "description": "Go5G Plus — Pat's Galaxy", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_004", "bill_id": "BILL_001", "line_id": None, "category": "credit", "description": "Autopay & paperless discount (3 lines)", "amount": -25.00, "is_recurring": "true"},
    # Device installments
    {"charge_id": "CHG_005", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "device_installment", "description": "iPhone 16 Pro installment (23 of 24)", "amount": 3.47, "is_recurring": "true"},
    {"charge_id": "CHG_006", "bill_id": "BILL_001", "line_id": "LINE_002", "category": "device_installment", "description": "iPhone 15 installment (6 of 24)", "amount": 24.99, "is_recurring": "true"},
    # Trade-in credit
    {"charge_id": "CHG_007", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "credit", "description": "Device trade-in credit (iPhone 14 Pro)", "amount": -16.67, "is_recurring": "true"},
    # Insurance
    {"charge_id": "CHG_008", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "insurance", "description": "Protection 360 — Jamie's iPhone", "amount": 18.00, "is_recurring": "true"},
    # Taxes & fees
    {"charge_id": "CHG_009", "bill_id": "BILL_001", "line_id": None, "category": "taxes_fees", "description": "Regulatory recovery fee", "amount": 3.49, "is_recurring": "true"},
    {"charge_id": "CHG_010", "bill_id": "BILL_001", "line_id": None, "category": "taxes_fees", "description": "Federal Universal Service Fund", "amount": 2.89, "is_recurring": "true"},
    {"charge_id": "CHG_011", "bill_id": "BILL_001", "line_id": None, "category": "taxes_fees", "description": "State and local taxes (CO)", "amount": 5.26, "is_recurring": "true"},
    {"charge_id": "CHG_012", "bill_id": "BILL_001", "line_id": None, "category": "taxes_fees", "description": "911 surcharge", "amount": 1.99, "is_recurring": "true"},
    # ONE-TIME charges (the surprise)
    {"charge_id": "CHG_013", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "international", "description": "International roaming — data usage in Canada (0.4 GB)", "amount": 29.00, "is_recurring": "false"},
    {"charge_id": "CHG_014", "bill_id": "BILL_001", "line_id": "LINE_001", "category": "one_time", "description": "Device Protection 360 claim deductible — screen repair", "amount": 5.00, "is_recurring": "false"},

    # ── BILL_002 (April, paid, $153.22) ──
    {"charge_id": "CHG_015", "bill_id": "BILL_002", "line_id": "LINE_001", "category": "plan", "description": "Go5G Plus — Jamie's iPhone", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_016", "bill_id": "BILL_002", "line_id": "LINE_002", "category": "plan", "description": "Go5G Plus — Riley's iPhone", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_017", "bill_id": "BILL_002", "line_id": "LINE_003", "category": "plan", "description": "Go5G Plus — Pat's Galaxy", "amount": 45.00, "is_recurring": "true"},
    {"charge_id": "CHG_018", "bill_id": "BILL_002", "line_id": None, "category": "credit", "description": "Autopay & paperless discount (3 lines)", "amount": -25.00, "is_recurring": "true"},
    {"charge_id": "CHG_019", "bill_id": "BILL_002", "line_id": "LINE_001", "category": "device_installment", "description": "iPhone 16 Pro installment (22 of 24)", "amount": 3.47, "is_recurring": "true"},
    {"charge_id": "CHG_020", "bill_id": "BILL_002", "line_id": "LINE_002", "category": "device_installment", "description": "iPhone 15 installment (5 of 24)", "amount": 24.99, "is_recurring": "true"},
    {"charge_id": "CHG_021", "bill_id": "BILL_002", "line_id": "LINE_001", "category": "credit", "description": "Device trade-in credit (iPhone 14 Pro)", "amount": -16.67, "is_recurring": "true"},
    {"charge_id": "CHG_022", "bill_id": "BILL_002", "line_id": "LINE_001", "category": "insurance", "description": "Protection 360 — Jamie's iPhone", "amount": 18.00, "is_recurring": "true"},
    {"charge_id": "CHG_023", "bill_id": "BILL_002", "line_id": None, "category": "taxes_fees", "description": "Taxes, fees & surcharges", "amount": 13.43, "is_recurring": "true"},
]

# ═══════════════════════════════════════════════════════════════════════════
#  SUPPORT TICKETS (3)
# ═══════════════════════════════════════════════════════════════════════════

SUPPORT_TICKETS = [
    {
        "ticket_id": "TKT_001", "customer_id": DEMO_USER_ID, "line_id": "LINE_001",
        "category": "network", "status": "in_progress",
        "created_at": ts(now - timedelta(days=3)),
        "resolved_at": None,
        "summary": "Slow data speeds at home in Denver since last week. Consistently getting under 5 Mbps on 5G.",
        "resolution": None,
    },
    {
        "ticket_id": "TKT_002", "customer_id": DEMO_USER_ID, "line_id": "LINE_001",
        "category": "device", "status": "resolved",
        "created_at": ts(now - timedelta(days=14)),
        "resolved_at": ts(now - timedelta(days=12)),
        "summary": "Screen crack on iPhone 16 Pro. Filed Protection 360 claim.",
        "resolution": "Claim approved. Screen repaired at authorized service center. $5 deductible applied to next bill.",
    },
    {
        "ticket_id": "TKT_003", "customer_id": "CUST_003", "line_id": "LINE_005",
        "category": "billing", "status": "open",
        "created_at": ts(now - timedelta(days=35)),
        "resolved_at": None,
        "summary": "Account suspended for non-payment. Customer requesting payment arrangement.",
        "resolution": None,
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  POLICY DOCUMENTS (10)
# ═══════════════════════════════════════════════════════════════════════════

POLICIES_TEXT = [
    {
        "doc_id": "POL_001", "title": "Device Return & Exchange Policy", "category": "devices",
        "content": (
            "Devices may be returned or exchanged within 14 calendar days of purchase. A $75 restocking fee applies "
            "to all returns and exchanges unless the device is defective. The device must be in its original condition "
            "with all accessories, packaging, and receipt. Devices purchased online can be returned in-store or by mail "
            "using the prepaid shipping label. Refunds are processed to the original payment method within 5-7 business days. "
            "Opened accessories (cases, chargers) are non-returnable. Gift cards and prepaid refill cards are final sale."
        ),
    },
    {
        "doc_id": "POL_002", "title": "Device Protection 360", "category": "insurance",
        "content": (
            "Device Protection 360 costs $18/month and covers loss, theft, accidental damage, and mechanical breakdown "
            "after the manufacturer warranty expires. Deductibles range from $29 for screen repair to $275 for full "
            "device replacement, depending on device tier. Customers may file up to 3 claims in a rolling 12-month period. "
            "Claims are fulfilled by Asurion within 24 hours for in-stock devices. A replacement device may be new or "
            "refurbished. Stolen device claims require a police report filed within 48 hours. Protection 360 also includes "
            "AppleCare Services for iPhones and Samsung Care for Galaxy devices. Cancel anytime — no penalty."
        ),
    },
    {
        "doc_id": "POL_003", "title": "International Roaming & Travel Pass", "category": "international",
        "content": (
            "R-Mobile offers International Travel Pass for use in 215+ countries and destinations. Canada & Mexico: "
            "$5/day, activated only on days you use your phone. All other countries: $12/day. Each pass includes unlimited "
            "talk, text, and 5 GB high-speed data per day. After 5 GB, speeds are reduced to 256 Kbps for the remainder "
            "of the day. Without a Travel Pass, international roaming rates apply: $0.25/minute for calls, $0.50 per text, "
            "and $2.00/MB for data. Go5G Plus and Go5G Next plans include international texting and 5 GB data in 215+ "
            "countries at no extra charge — but voice calls still require a Travel Pass or are billed at $0.25/minute. "
            "Travel Pass can be added through the app, online, or by calling customer service."
        ),
    },
    {
        "doc_id": "POL_004", "title": "Bill Dispute & Account Credits", "category": "billing",
        "content": (
            "Customers may dispute charges within 60 days of the bill date. To initiate a dispute, contact customer "
            "service by phone, chat, or in-store. Provide the bill date, charge description, and reason for dispute. "
            "Credits for valid disputes are typically applied within 1-2 billing cycles. If the dispute involves a "
            "third-party charge, R-Mobile will block future third-party billing on the account upon request. For "
            "recurring billing errors, a retroactive credit for up to 3 billing cycles may be applied. Escalation path: "
            "customer service representative → supervisor → executive customer relations → FCC/BBB complaint."
        ),
    },
    {
        "doc_id": "POL_005", "title": "Device Unlock Policy", "category": "devices",
        "content": (
            "R-Mobile will unlock a device when the following conditions are met: (1) the device must be fully paid off — "
            "no remaining installment balance, (2) the device must have been active on the R-Mobile network for at least "
            "40 days, (3) the associated account must be in good standing with no past-due balance, (4) the device must "
            "not be reported as lost or stolen. Military personnel deployed overseas may request an unlock regardless of "
            "the 40-day requirement. Unlock requests can be submitted through the app, online, or by calling customer "
            "service. Processing takes 24-72 hours. Once unlocked, the device can be used on any compatible carrier."
        ),
    },
    {
        "doc_id": "POL_006", "title": "Trade-In Program", "category": "devices",
        "content": (
            "Trade in your current device toward a new one. Eligible devices are assessed based on condition: screen, "
            "buttons, and power must all be fully functional. Cracked screens or water damage reduce trade-in value. "
            "Trade-in credit is applied as monthly bill credits over 24 months, not as a one-time discount. If you cancel "
            "your line before 24 months, remaining credits are forfeited. You have 30 days after activating your new device "
            "to send in the trade-in — either by mail (prepaid label provided) or at any R-Mobile store. Devices not "
            "received within 30 days forfeit the trade-in credit and a charge for the full credit amount will be applied. "
            "Example: iPhone 15 Pro in good condition qualifies for up to $800 in credits toward iPhone 16 Pro."
        ),
    },
    {
        "doc_id": "POL_007", "title": "Plan Changes & Cancellation", "category": "plans",
        "content": (
            "Plan changes take effect at the start of the next billing cycle. Upgrading to a higher-tier plan can be "
            "backdated to the current cycle if requested within the first 7 days. There is no early termination fee (ETF) "
            "for postpaid plans — R-Mobile is contract-free. However, cancelling a line with an active device installment "
            "plan requires paying the remaining device balance in full on the final bill. Promotional credits (e.g., "
            "free line, BOGO, trade-in credits) are forfeited upon cancellation of the associated line. The final bill "
            "is prorated based on the cancellation date. Port-out to another carrier initiates automatic cancellation "
            "of the line within 24-48 hours."
        ),
    },
    {
        "doc_id": "POL_008", "title": "Payment Arrangements & Extensions", "category": "billing",
        "content": (
            "If you cannot pay your bill by the due date, you may request a payment arrangement for up to 14 days. "
            "Payment arrangements can be set up through the app, online, or by calling customer service. Only one "
            "arrangement is allowed per billing cycle. If a payment arrangement is broken (payment not received by the "
            "extended date), the account may be subject to a late fee of $5.00 and the next arrangement eligibility is "
            "reset. Service is suspended after 60 days past due. After 90 days, the account is sent to collections. "
            "Partial payments are accepted and applied to the oldest outstanding balance first."
        ),
    },
    {
        "doc_id": "POL_009", "title": "Taxes, Fees & Surcharges Explained", "category": "billing",
        "content": (
            "Your R-Mobile bill may include the following taxes and fees: (1) Regulatory Recovery Fee ($1.16/line/month) — "
            "helps cover costs of regulatory compliance. (2) Federal Universal Service Fund (varies) — federally mandated "
            "charge supporting rural and low-income phone service. (3) State and local taxes — vary by jurisdiction; "
            "Colorado averages 4.2% of service charges. (4) 911 surcharge ($0.66/line/month in CO) — funds local emergency "
            "services. (5) Administrative fee ($0.39/line/month). These charges are not optional and appear on every bill. "
            "R-Mobile plans advertise 'taxes and fees included' pricing for Go5G and above — meaning these charges are "
            "absorbed into the plan cost and do not appear as separate line items."
        ),
    },
    {
        "doc_id": "POL_010", "title": "Account Security & Fraud Prevention", "category": "account",
        "content": (
            "Protect your account with these security features: (1) Account PIN — a 6-8 digit PIN required for all "
            "account changes. Set or change via the app or in-store with valid ID. (2) SIM Lock — prevents unauthorized "
            "SIM swaps. Enable through the app under Account Security. (3) Port-Out Protection — blocks unauthorized "
            "number transfers to other carriers. Enabled by default on all accounts. (4) If you suspect fraud or "
            "unauthorized access, call 611 immediately. R-Mobile will freeze the account, reverse unauthorized changes, "
            "and issue replacement SIMs within 24 hours. Customers affected by identity theft should also file a report "
            "at identitytheft.gov and provide a copy to R-Mobile for account notation."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def write_jsonl(output_dir: Path, filename: str, rows: list[dict]) -> int:
    path = output_dir / filename
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return
    lines = env_path.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_demo_data(
    *,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Embed policy content
    policy_texts = [p["content"] for p in POLICIES_TEXT]
    embeddings = embed(policy_texts)
    policies = []
    for policy, emb in zip(POLICIES_TEXT, embeddings):
        policies.append({**policy, "content_embedding": emb})

    # Write all JSONL files
    summary: dict[str, int] = {}
    summary["customers"] = write_jsonl(out, "customers.jsonl", CUSTOMERS)
    summary["lines"] = write_jsonl(out, "lines.jsonl", LINES)
    summary["plans"] = write_jsonl(out, "plans.jsonl", PLANS)
    summary["devices"] = write_jsonl(out, "devices.jsonl", DEVICES)
    summary["bills"] = write_jsonl(out, "bills.jsonl", BILLS)
    summary["bill_charges"] = write_jsonl(out, "bill_charges.jsonl", BILL_CHARGES)
    summary["support_tickets"] = write_jsonl(out, "support_tickets.jsonl", SUPPORT_TICKETS)
    summary["policy_docs"] = write_jsonl(out, "policy_docs.jsonl", policies)

    env_updates = {
        "DEMO_USER_ID": DEMO_USER_ID,
        "DEMO_USER_NAME": "Jamie Torres",
        "DEMO_USER_EMAIL": "jamie.torres@example.com",
    }

    if update_env_file:
        for k, v in env_updates.items():
            update_env(k, v)

    return GeneratedDataset(
        output_dir=str(out),
        env_updates=env_updates,
        summary=summary,
    )


if __name__ == "__main__":
    result = generate_demo_data(update_env_file=True)
    print(f"Generated R-Mobile demo data in {result.output_dir}")
    for entity, count in result.summary.items():
        print(f"  {entity}: {count}")
