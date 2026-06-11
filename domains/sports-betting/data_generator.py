"""Generate sample data for the sports betting demo."""

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

OUTPUT_DIR = ROOT / "output" / "sports-betting"
DEMO_PLAYER_ID = "PLY_DEMO_001"
NOW = datetime(2026, 5, 21, 22, 10, tzinfo=timezone.utc)


def ts(dt: datetime) -> str:
    return dt.isoformat()


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    client = openai.OpenAI()
    resp = client.embeddings.create(
        input=texts,
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return [item.embedding for item in resp.data]


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


PLAYERS = [
    {
        "player_id": DEMO_PLAYER_ID,
        "name": "Maya Shah",
        "email": "maya.shah@example.com",
        "phone": "+44-7700-900101",
        "account_status": "active",
        "kyc_status": "verified",
        "home_jurisdiction": "United Kingdom",
        "preferred_sports": "football, horse racing",
        "responsible_gaming_level": "standard",
        "deposit_limit_weekly": 150.00,
        "account_created_at": ts(NOW - timedelta(days=540)),
    },
    {
        "player_id": "PLY_002",
        "name": "Oliver Grant",
        "email": "oliver.grant@example.com",
        "phone": "+44-7700-900202",
        "account_status": "active",
        "kyc_status": "verified",
        "home_jurisdiction": "United Kingdom",
        "preferred_sports": "football, tennis",
        "responsible_gaming_level": "watch",
        "deposit_limit_weekly": 75.00,
        "account_created_at": ts(NOW - timedelta(days=300)),
    },
    {
        "player_id": "PLY_003",
        "name": "Sofia Rossi",
        "email": "sofia.rossi@example.com",
        "phone": "+39-320-555-0103",
        "account_status": "active",
        "kyc_status": "verified",
        "home_jurisdiction": "Italy",
        "preferred_sports": "tennis, basketball",
        "responsible_gaming_level": "standard",
        "deposit_limit_weekly": 200.00,
        "account_created_at": ts(NOW - timedelta(days=725)),
    },
    {
        "player_id": "PLY_004",
        "name": "Noah Jensen",
        "email": "noah.jensen@example.com",
        "phone": "+45-20-55-0104",
        "account_status": "suspended",
        "kyc_status": "review_required",
        "home_jurisdiction": "Denmark",
        "preferred_sports": "football",
        "responsible_gaming_level": "protected",
        "deposit_limit_weekly": 0.00,
        "account_created_at": ts(NOW - timedelta(days=120)),
    },
    {
        "player_id": "PLY_005",
        "name": "Aisha Khan",
        "email": "aisha.khan@example.com",
        "phone": "+44-7700-900505",
        "account_status": "active",
        "kyc_status": "pending",
        "home_jurisdiction": "United Kingdom",
        "preferred_sports": "horse racing",
        "responsible_gaming_level": "standard",
        "deposit_limit_weekly": 100.00,
        "account_created_at": ts(NOW - timedelta(days=42)),
    },
]


SPORT_EVENTS = [
    {
        "event_id": "SEVT_001",
        "sport": "football",
        "league": "Premier League",
        "event_name": "Merseyside Reds vs Manchester Blues",
        "start_time": ts(NOW - timedelta(hours=4)),
        "status": "final",
        "score": "Merseyside Reds 2-1 Manchester Blues",
        "venue": "Northbank Stadium",
    },
    {
        "event_id": "SEVT_002",
        "sport": "football",
        "league": "Premier League",
        "event_name": "North London vs West London",
        "start_time": ts(NOW + timedelta(days=1, hours=2)),
        "status": "scheduled",
        "score": None,
        "venue": "Capital Arena",
    },
    {
        "event_id": "SEVT_003",
        "sport": "horse racing",
        "league": "Cheltenham Evening Card",
        "event_name": "Cheltenham 19:40 Sprint Handicap",
        "start_time": ts(NOW - timedelta(hours=2, minutes=30)),
        "status": "final",
        "score": "Silver Comet won by 1.5 lengths",
        "venue": "Cheltenham",
    },
    {
        "event_id": "SEVT_005",
        "sport": "football",
        "league": "Championship",
        "event_name": "Birmingham Lions vs Seaside Albion",
        "start_time": ts(NOW - timedelta(days=2, hours=1)),
        "status": "final",
        "score": "Birmingham Lions 1-0 Seaside Albion",
        "venue": "Midlands Park",
    },
    {
        "event_id": "SEVT_004",
        "sport": "tennis",
        "league": "Madrid Open",
        "event_name": "Elena Ruiz vs Clara Novak",
        "start_time": ts(NOW + timedelta(hours=18)),
        "status": "scheduled",
        "score": None,
        "venue": "Madrid Centre Court",
    },
]


MARKETS = [
    {
        "market_id": "MKT_001",
        "event_id": "SEVT_001",
        "market_type": "match_winner",
        "selection_name": "Merseyside Reds",
        "odds_decimal": 2.20,
        "market_status": "settled",
        "result": "won",
        "last_price_move_at": ts(NOW - timedelta(hours=4, minutes=15)),
        "trading_note": "Result received from official feed but settlement queue flagged for manual review due to late correction.",
    },
    {
        "market_id": "MKT_002",
        "event_id": "SEVT_001",
        "market_type": "both_teams_to_score",
        "selection_name": "Yes",
        "odds_decimal": 1.75,
        "market_status": "settled",
        "result": "won",
        "last_price_move_at": ts(NOW - timedelta(hours=4, minutes=5)),
        "trading_note": "Settled automatically from official feed.",
    },
    {
        "market_id": "MKT_003",
        "event_id": "SEVT_001",
        "market_type": "total_goals",
        "selection_name": "Over 2.5 goals",
        "odds_decimal": 1.92,
        "market_status": "settled",
        "result": "won",
        "last_price_move_at": ts(NOW - timedelta(hours=4, minutes=2)),
        "trading_note": "Settled automatically from official feed.",
    },
    {
        "market_id": "MKT_004",
        "event_id": "SEVT_002",
        "market_type": "match_winner",
        "selection_name": "North London",
        "odds_decimal": 2.05,
        "market_status": "open",
        "result": "pending",
        "last_price_move_at": ts(NOW - timedelta(minutes=40)),
        "trading_note": "Market open. Cash out enabled on eligible singles before kickoff.",
    },
    {
        "market_id": "MKT_005",
        "event_id": "SEVT_003",
        "market_type": "each_way",
        "selection_name": "Silver Comet",
        "odds_decimal": 5.50,
        "market_status": "settled",
        "result": "won",
        "last_price_move_at": ts(NOW - timedelta(hours=3)),
        "trading_note": "Starting price confirmed.",
    },
    {
        "market_id": "MKT_007",
        "event_id": "SEVT_005",
        "market_type": "match_winner",
        "selection_name": "Birmingham Lions",
        "odds_decimal": 2.80,
        "market_status": "settled",
        "result": "won",
        "last_price_move_at": ts(NOW - timedelta(days=2, hours=1, minutes=20)),
        "trading_note": "Settled automatically after full time.",
    },
    {
        "market_id": "MKT_006",
        "event_id": "SEVT_004",
        "market_type": "match_winner",
        "selection_name": "Elena Ruiz",
        "odds_decimal": 1.80,
        "market_status": "open",
        "result": "pending",
        "last_price_move_at": ts(NOW - timedelta(minutes=20)),
        "trading_note": "Market open with normal liquidity.",
    },
]


BET1_PLACED = NOW - timedelta(hours=5, minutes=5)
BET2_PLACED = NOW - timedelta(days=2, hours=3)
BET3_PLACED = NOW - timedelta(hours=3, minutes=10)
BET4_PLACED = NOW - timedelta(minutes=35)

BETS = [
    {
        "bet_id": "BET_001",
        "player_id": DEMO_PLAYER_ID,
        "bet_type": "accumulator",
        "status": "pending_settlement",
        "stake": 20.00,
        "potential_return": 147.84,
        "placed_at": ts(BET1_PLACED),
        "settled_at": None,
        "channel": "mobile",
        "currency": "GBP",
        "cashout_available": False,
        "cashout_value": None,
        "risk_flag": "none",
        "summary": "Football treble: Merseyside Reds win, both teams to score, over 2.5 goals.",
    },
    {
        "bet_id": "BET_002",
        "player_id": DEMO_PLAYER_ID,
        "bet_type": "single",
        "status": "won",
        "stake": 10.00,
        "potential_return": 28.00,
        "placed_at": ts(BET2_PLACED),
        "settled_at": ts(BET2_PLACED + timedelta(hours=3, minutes=15)),
        "channel": "web",
        "currency": "GBP",
        "cashout_available": False,
        "cashout_value": None,
        "risk_flag": "none",
        "summary": "Football single: Birmingham Lions to win.",
    },
    {
        "bet_id": "BET_003",
        "player_id": DEMO_PLAYER_ID,
        "bet_type": "each_way",
        "status": "lost",
        "stake": 5.00,
        "potential_return": 27.50,
        "placed_at": ts(BET3_PLACED),
        "settled_at": ts(NOW - timedelta(hours=1, minutes=35)),
        "channel": "mobile",
        "currency": "GBP",
        "cashout_available": False,
        "cashout_value": None,
        "risk_flag": "none",
        "summary": "Horse racing each-way: Red Lantern in the Cheltenham Sprint Handicap.",
    },
    {
        "bet_id": "BET_004",
        "player_id": DEMO_PLAYER_ID,
        "bet_type": "single",
        "status": "open",
        "stake": 12.00,
        "potential_return": 24.60,
        "placed_at": ts(BET4_PLACED),
        "settled_at": None,
        "channel": "mobile",
        "currency": "GBP",
        "cashout_available": True,
        "cashout_value": 11.40,
        "risk_flag": "none",
        "summary": "Football single: North London to win tomorrow.",
    },
    {
        "bet_id": "BET_005",
        "player_id": "PLY_002",
        "bet_type": "single",
        "status": "open",
        "stake": 40.00,
        "potential_return": 72.00,
        "placed_at": ts(NOW - timedelta(minutes=25)),
        "settled_at": None,
        "channel": "web",
        "currency": "GBP",
        "cashout_available": True,
        "cashout_value": 38.00,
        "risk_flag": "responsible_gaming",
        "summary": "Tennis single: Elena Ruiz to win.",
    },
    {
        "bet_id": "BET_006",
        "player_id": "PLY_003",
        "bet_type": "single",
        "status": "void",
        "stake": 15.00,
        "potential_return": 31.50,
        "placed_at": ts(NOW - timedelta(days=1)),
        "settled_at": ts(NOW - timedelta(days=1) + timedelta(hours=2)),
        "channel": "mobile",
        "currency": "EUR",
        "cashout_available": False,
        "cashout_value": None,
        "risk_flag": "none",
        "summary": "Basketball player-points market voided after lineup correction.",
    },
]


BET_LEGS = [
    {
        "leg_id": "LEG_001",
        "bet_id": "BET_001",
        "event_id": "SEVT_001",
        "market_id": "MKT_001",
        "event_name": "Merseyside Reds vs Manchester Blues",
        "market_type": "match_winner",
        "selection_name": "Merseyside Reds",
        "odds_decimal": 2.20,
        "leg_status": "won",
        "result_detail": "Merseyside Reds won 2-1; result is in trading review after a late official-feed correction.",
    },
    {
        "leg_id": "LEG_002",
        "bet_id": "BET_001",
        "event_id": "SEVT_001",
        "market_id": "MKT_002",
        "event_name": "Merseyside Reds vs Manchester Blues",
        "market_type": "both_teams_to_score",
        "selection_name": "Yes",
        "odds_decimal": 1.75,
        "leg_status": "won",
        "result_detail": "Both teams scored.",
    },
    {
        "leg_id": "LEG_003",
        "bet_id": "BET_001",
        "event_id": "SEVT_001",
        "market_id": "MKT_003",
        "event_name": "Merseyside Reds vs Manchester Blues",
        "market_type": "total_goals",
        "selection_name": "Over 2.5 goals",
        "odds_decimal": 1.92,
        "leg_status": "won",
        "result_detail": "Three total goals were scored.",
    },
    {
        "leg_id": "LEG_004",
        "bet_id": "BET_002",
        "event_id": "SEVT_005",
        "market_id": "MKT_007",
        "event_name": "Birmingham Lions vs Seaside Albion",
        "market_type": "match_winner",
        "selection_name": "Birmingham Lions",
        "odds_decimal": 2.80,
        "leg_status": "won",
        "result_detail": "Birmingham Lions won 1-0.",
    },
    {
        "leg_id": "LEG_005",
        "bet_id": "BET_003",
        "event_id": "SEVT_003",
        "market_id": "MKT_005",
        "event_name": "Cheltenham 19:40 Sprint Handicap",
        "market_type": "each_way",
        "selection_name": "Red Lantern",
        "odds_decimal": 5.50,
        "leg_status": "lost",
        "result_detail": "Red Lantern finished outside the each-way places.",
    },
    {
        "leg_id": "LEG_006",
        "bet_id": "BET_004",
        "event_id": "SEVT_002",
        "market_id": "MKT_004",
        "event_name": "North London vs West London",
        "market_type": "match_winner",
        "selection_name": "North London",
        "odds_decimal": 2.05,
        "leg_status": "open",
        "result_detail": "Event has not started.",
    },
    {
        "leg_id": "LEG_007",
        "bet_id": "BET_005",
        "event_id": "SEVT_004",
        "market_id": "MKT_006",
        "event_name": "Elena Ruiz vs Clara Novak",
        "market_type": "match_winner",
        "selection_name": "Elena Ruiz",
        "odds_decimal": 1.80,
        "leg_status": "open",
        "result_detail": "Event has not started.",
    },
]


BET_SETTLEMENT_EVENTS = [
    {
        "settlement_event_id": "SETTLE_001",
        "bet_id": "BET_001",
        "event_type": "placed",
        "timestamp": ts(BET1_PLACED),
        "description": "Player placed a three-leg football accumulator on mobile.",
        "actor": "player",
    },
    {
        "settlement_event_id": "SETTLE_002",
        "bet_id": "BET_001",
        "event_type": "event_final",
        "timestamp": ts(NOW - timedelta(hours=1, minutes=20)),
        "description": "Football event reached full time with a 2-1 result.",
        "actor": "feed",
    },
    {
        "settlement_event_id": "SETTLE_003",
        "bet_id": "BET_001",
        "event_type": "result_received",
        "timestamp": ts(NOW - timedelta(hours=1, minutes=13)),
        "description": "Both teams to score and total-goals legs settled automatically as won.",
        "actor": "system",
    },
    {
        "settlement_event_id": "SETTLE_004",
        "bet_id": "BET_001",
        "event_type": "review_started",
        "timestamp": ts(NOW - timedelta(minutes=52)),
        "description": "Match-winner leg entered trading review after a late official-feed correction.",
        "actor": "trading",
    },
    {
        "settlement_event_id": "SETTLE_005",
        "bet_id": "BET_002",
        "event_type": "bet_settled",
        "timestamp": ts(BET2_PLACED + timedelta(hours=3, minutes=15)),
        "description": "Single football bet settled as won.",
        "actor": "system",
    },
    {
        "settlement_event_id": "SETTLE_006",
        "bet_id": "BET_002",
        "event_type": "payout_credited",
        "timestamp": ts(BET2_PLACED + timedelta(hours=3, minutes=16)),
        "description": "Payout credited to player wallet.",
        "actor": "system",
    },
    {
        "settlement_event_id": "SETTLE_007",
        "bet_id": "BET_003",
        "event_type": "bet_settled",
        "timestamp": ts(NOW - timedelta(hours=1, minutes=35)),
        "description": "Each-way racing bet settled as lost.",
        "actor": "system",
    },
]


WALLET_TRANSACTIONS = [
    {
        "transaction_id": "TXN_001",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": None,
        "transaction_type": "deposit",
        "amount": 75.00,
        "balance_after": 75.00,
        "status": "completed",
        "created_at": ts(NOW - timedelta(days=2, hours=4)),
        "payment_method": "visa_4242",
        "processor_reference": "PSP_DEP_001",
    },
    {
        "transaction_id": "TXN_002",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_001",
        "transaction_type": "stake",
        "amount": -20.00,
        "balance_after": 55.00,
        "status": "completed",
        "created_at": ts(BET1_PLACED),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_STAKE_001",
    },
    {
        "transaction_id": "TXN_003",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_002",
        "transaction_type": "stake",
        "amount": -10.00,
        "balance_after": 45.00,
        "status": "completed",
        "created_at": ts(BET2_PLACED),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_STAKE_002",
    },
    {
        "transaction_id": "TXN_004",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_002",
        "transaction_type": "payout",
        "amount": 28.00,
        "balance_after": 73.00,
        "status": "completed",
        "created_at": ts(BET2_PLACED + timedelta(hours=3, minutes=16)),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_PAYOUT_002",
    },
    {
        "transaction_id": "TXN_005",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_003",
        "transaction_type": "stake",
        "amount": -5.00,
        "balance_after": 68.00,
        "status": "completed",
        "created_at": ts(BET3_PLACED),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_STAKE_003",
    },
    {
        "transaction_id": "TXN_006",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_004",
        "transaction_type": "stake",
        "amount": -12.00,
        "balance_after": 56.00,
        "status": "completed",
        "created_at": ts(BET4_PLACED),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_STAKE_004",
    },
    {
        "transaction_id": "TXN_007",
        "player_id": "PLY_002",
        "bet_id": "BET_005",
        "transaction_type": "stake",
        "amount": -40.00,
        "balance_after": 35.00,
        "status": "held",
        "created_at": ts(NOW - timedelta(minutes=25)),
        "payment_method": "wallet",
        "processor_reference": "LEDGER_STAKE_005",
    },
]


SUPPORT_TICKETS = [
    {
        "ticket_id": "TKT_001",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_001",
        "category": "settlement_delay",
        "status": "open",
        "created_at": ts(NOW - timedelta(minutes=30)),
        "resolved_at": None,
        "summary": "Player asked why football accumulator has not settled after the match ended.",
        "resolution": None,
    },
    {
        "ticket_id": "TKT_002",
        "player_id": DEMO_PLAYER_ID,
        "bet_id": "BET_003",
        "category": "settlement",
        "status": "resolved",
        "created_at": ts(NOW - timedelta(hours=1, minutes=20)),
        "resolved_at": ts(NOW - timedelta(hours=1, minutes=10)),
        "summary": "Player asked why each-way racing bet returned no payout.",
        "resolution": "Support explained that the selection finished outside each-way places.",
    },
    {
        "ticket_id": "TKT_003",
        "player_id": "PLY_002",
        "bet_id": "BET_005",
        "category": "responsible_gaming",
        "status": "in_progress",
        "created_at": ts(NOW - timedelta(minutes=10)),
        "resolved_at": None,
        "summary": "Player tried to raise deposit limit while account was under safer-gambling review.",
        "resolution": None,
    },
]


POLICIES_TEXT = [
    {
        "policy_id": "POL_001",
        "title": "Bet Settlement Timing",
        "category": "settlement",
        "content": (
            "Most pre-match and in-play bets settle within a few minutes of official result confirmation. "
            "Accumulators settle only after every leg has a verified result. If an official data feed sends a "
            "late correction or conflict, the relevant leg may enter trading review. Reviewed results are "
            "usually resolved within 60 minutes of official confirmation, but payout is not credited until "
            "verification is complete."
        ),
    },
    {
        "policy_id": "POL_002",
        "title": "Accumulator Settlement",
        "category": "settlement",
        "content": (
            "An accumulator requires every leg to win for the bet to pay out. A single losing leg makes the "
            "accumulator lose, and a void leg may reduce the accumulator according to the remaining valid legs. "
            "When one leg is pending review, the whole accumulator remains pending until that leg is settled."
        ),
    },
    {
        "policy_id": "POL_003",
        "title": "Cash Out Availability",
        "category": "cashout",
        "content": (
            "Cash out is discretionary and may be available on eligible open bets before an event starts or "
            "while a market is live. Cash out can be suspended when markets are suspended, an event is close "
            "to starting, official data is delayed, or trading review is active. Cash out is not available "
            "for bets that are already settled or pending final settlement review."
        ),
    },
    {
        "policy_id": "POL_004",
        "title": "Safer Gambling Limits",
        "category": "responsible_gaming",
        "content": (
            "Players can set deposit, stake, loss, and session limits. Limit decreases apply immediately; "
            "limit increases require a cooling-off period and may require additional review. Support agents "
            "should not encourage players to increase limits or chase losses. If a player expresses concern, "
            "agents should provide limit, timeout, and self-exclusion options."
        ),
    },
    {
        "policy_id": "POL_005",
        "title": "Void Bets and Market Corrections",
        "category": "settlement",
        "content": (
            "Markets may be voided or corrected when an event is abandoned, a runner is withdrawn, pricing "
            "was materially incorrect, or official result data changes. Stakes on void selections are returned "
            "unless sport-specific rules state otherwise. Corrections are audited by the trading team."
        ),
    },
    {
        "policy_id": "POL_006",
        "title": "Payment and Withdrawal Checks",
        "category": "wallet",
        "content": (
            "Withdrawals are processed after account, KYC, payment-method, and anti-financial-crime checks. "
            "Recent deposits, bonus conditions, or open settlement reviews may delay withdrawal availability. "
            "Completed wallet payouts from settled bets are shown as payout transactions."
        ),
    },
    {
        "policy_id": "POL_007",
        "title": "Sports Integrity Monitoring",
        "category": "integrity",
        "content": (
            "Suspicious betting patterns, event-integrity alerts, or unusual market movements may trigger "
            "additional review. The sportsbook may temporarily suspend markets or delay settlement while "
            "integrity checks are completed in regulated markets."
        ),
    },
    {
        "policy_id": "POL_008",
        "title": "Customer Protection Communications",
        "category": "responsible_gaming",
        "content": (
            "Customer communications must be clear, balanced, and supportive. Agents should explain available "
            "controls and support without promotional pressure. Where account activity indicates risk, agents "
            "should prioritize player protection and signpost safer-gambling tools."
        ),
    },
]


def write_jsonl(output_dir: Path, filename: str, rows: list[dict]) -> None:
    path = output_dir / filename
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"  {path.name}: {len(rows)} records")


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    safe_value = f'"{value}"' if " " in value else value
    if not env_path.exists():
        env_path.write_text(f"{key}={safe_value}\n", encoding="utf-8")
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={safe_value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={safe_value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_demo_data(
    *,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    del seed
    resolved_output_dir = output_dir or OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating embeddings for sportsbook policies...")
    contents = [p["content"] for p in POLICIES_TEXT]
    embeddings = embed(contents)
    policies = [{**p, "content_embedding": emb} for p, emb in zip(POLICIES_TEXT, embeddings)]

    print("Writing JSONL files:")
    write_jsonl(resolved_output_dir, "players.jsonl", PLAYERS)
    write_jsonl(resolved_output_dir, "sport_events.jsonl", SPORT_EVENTS)
    write_jsonl(resolved_output_dir, "markets.jsonl", MARKETS)
    write_jsonl(resolved_output_dir, "bets.jsonl", BETS)
    write_jsonl(resolved_output_dir, "bet_legs.jsonl", BET_LEGS)
    write_jsonl(resolved_output_dir, "bet_settlement_events.jsonl", BET_SETTLEMENT_EVENTS)
    write_jsonl(resolved_output_dir, "wallet_transactions.jsonl", WALLET_TRANSACTIONS)
    write_jsonl(resolved_output_dir, "support_tickets.jsonl", SUPPORT_TICKETS)
    write_jsonl(resolved_output_dir, "policies.jsonl", policies)

    demo = PLAYERS[0]
    env_updates = {
        "DEMO_USER_ID": demo["player_id"],
        "DEMO_USER_NAME": demo["name"],
        "DEMO_USER_EMAIL": demo["email"],
        "CTX_SURFACE_NAME": '"Sportsbook Context Surface"',
        "CTX_AGENT_NAME": '"Sports Desk Agent"',
        "REDIS_INSTANCE_NAME": '"Sports Desk Redis Cloud"',
    }
    if update_env_file:
        for key, value in env_updates.items():
            update_env(key, value)
    print(f"\nDemo user: {demo['name']} ({demo['player_id']})")
    print("Done.")

    return GeneratedDataset(
        output_dir=str(resolved_output_dir),
        env_updates=env_updates,
        summary={
            "players": len(PLAYERS),
            "sport_events": len(SPORT_EVENTS),
            "markets": len(MARKETS),
            "bets": len(BETS),
            "bet_legs": len(BET_LEGS),
            "bet_settlement_events": len(BET_SETTLEMENT_EVENTS),
            "wallet_transactions": len(WALLET_TRANSACTIONS),
            "support_tickets": len(SUPPORT_TICKETS),
            "policies": len(POLICIES_TEXT),
        },
    )


def main() -> None:
    generate_demo_data(output_dir=OUTPUT_DIR, update_env_file=True)


if __name__ == "__main__":
    main()
