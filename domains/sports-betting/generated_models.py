"""Generated Context Surface models for the Sports Desk domain."""

from __future__ import annotations

from typing import Any

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class Player(ContextModel):
    """Player entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_player:{player_id}"

    player_id: str = ContextField(
        description="Unique player identifier",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Player full name",
        index="text",
        weight=2.0,
    )

    email: str = ContextField(
        description="Player email",
        index="text",
        weight=1.5,
        no_stem=True,
    )

    phone: str | None = ContextField(
        description="Phone number",
    )

    account_status: str = ContextField(
        description="Account status: active, suspended, self_excluded",
        index="tag",
    )

    kyc_status: str = ContextField(
        description="KYC status: verified, pending, review_required",
        index="tag",
    )

    home_jurisdiction: str = ContextField(
        description="Regulated market or country for the player",
        index="tag",
    )

    preferred_sports: str = ContextField(
        description="Comma-separated preferred sports",
        index="text",
    )

    responsible_gaming_level: str = ContextField(
        description="Safer gambling profile: standard, watch, protected",
        index="tag",
    )

    deposit_limit_weekly: float = ContextField(
        description="Weekly deposit limit in account currency",
        index="numeric",
    )

    account_created_at: str = ContextField(
        description="ISO timestamp of account creation",
    )

    bets: Any = ContextRelationship(
        description="Bets placed by this player",
        target="Bet",
        source_field="player_id",
    )

    wallet_transactions: Any = ContextRelationship(
        description="Wallet transactions for this player",
        target="WalletTransaction",
        source_field="player_id",
    )


class SportEvent(ContextModel):
    """SportEvent entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_event:{event_id}"

    event_id: str = ContextField(
        description="Unique sport event identifier",
        is_key_component=True,
    )

    sport: str = ContextField(
        description="Sport name",
        index="tag",
    )

    league: str = ContextField(
        description="Competition or league",
        index="tag",
    )

    event_name: str = ContextField(
        description="Event display name",
        index="text",
        weight=2.0,
    )

    start_time: str = ContextField(
        description="ISO timestamp when the event starts",
    )

    status: str = ContextField(
        description="Event status: scheduled, live, final, abandoned",
        index="tag",
    )

    score: str | None = ContextField(
        description="Current or final score/result",
        index="text",
    )

    venue: str | None = ContextField(
        description="Venue or track",
    )

    markets: Any = ContextRelationship(
        description="Betting markets offered for this event",
        target="Market",
        source_field="event_id",
    )


class Market(ContextModel):
    """Market entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_market:{market_id}"

    market_id: str = ContextField(
        description="Unique market identifier",
        is_key_component=True,
    )

    event_id: str = ContextField(
        description="Related sport event",
        index="tag",
    )

    market_type: str = ContextField(
        description="Market type: match_winner, total_goals, both_teams_to_score, each_way",
        index="tag",
    )

    selection_name: str = ContextField(
        description="Selection or runner name",
        index="text",
        weight=1.5,
    )

    odds_decimal: float = ContextField(
        description="Current decimal odds",
        index="numeric",
        sortable=True,
    )

    market_status: str = ContextField(
        description="Market status: open, suspended, settled, void",
        index="tag",
    )

    result: str | None = ContextField(
        description="Result for this market: won, lost, void, pending",
        index="tag",
    )

    last_price_move_at: str | None = ContextField(
        description="ISO timestamp of latest odds update",
    )

    trading_note: str | None = ContextField(
        description="Trading desk note or reason for current market status",
        index="text",
    )

    event: Any = ContextRelationship(
        description="Sport event for this market",
        target="SportEvent",
        source_field="event_id",
    )


class Bet(ContextModel):
    """Bet entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_bet:{bet_id}"

    bet_id: str = ContextField(
        description="Unique bet identifier",
        is_key_component=True,
    )

    player_id: str = ContextField(
        description="Player who placed the bet",
        index="tag",
    )

    bet_type: str = ContextField(
        description="Bet type: single, accumulator, each_way",
        index="tag",
    )

    status: str = ContextField(
        description="Bet status: open, won, lost, void, pending_settlement, cashed_out",
        index="tag",
    )

    stake: float = ContextField(
        description="Stake amount",
        index="numeric",
        sortable=True,
    )

    potential_return: float = ContextField(
        description="Maximum possible return",
        index="numeric",
        sortable=True,
    )

    placed_at: str = ContextField(
        description="ISO timestamp when the bet was placed",
    )

    settled_at: str | None = ContextField(
        description="ISO timestamp when the bet settled",
    )

    channel: str = ContextField(
        description="Bet channel: mobile, web, retail",
        index="tag",
    )

    currency: str = ContextField(
        description="Account currency",
        index="tag",
    )

    cashout_available: bool = ContextField(
        description="Whether cash out is currently available",
    )

    cashout_value: float | None = ContextField(
        description="Current cash-out value if available",
        index="numeric",
    )

    risk_flag: str = ContextField(
        description="Risk flag: none, affordability_review, integrity_review, responsible_gaming",
        index="tag",
    )

    summary: str = ContextField(
        description="Human-readable bet summary",
        index="text",
    )

    player: Any = ContextRelationship(
        description="Player who placed the bet",
        target="Player",
        source_field="player_id",
    )

    legs: Any = ContextRelationship(
        description="Individual selections for this bet",
        target="BetLeg",
        source_field="bet_id",
    )

    settlement_events: Any = ContextRelationship(
        description="Settlement timeline for this bet",
        target="BetSettlementEvent",
        source_field="bet_id",
    )


class BetLeg(ContextModel):
    """BetLeg entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_bet_leg:{leg_id}"

    leg_id: str = ContextField(
        description="Unique bet-leg identifier",
        is_key_component=True,
    )

    bet_id: str = ContextField(
        description="Parent bet",
        index="tag",
    )

    event_id: str = ContextField(
        description="Related sport event",
        index="tag",
    )

    market_id: str = ContextField(
        description="Related market",
        index="tag",
    )

    event_name: str = ContextField(
        description="Denormalized event display name",
        index="text",
    )

    market_type: str = ContextField(
        description="Market type for this selection",
        index="tag",
    )

    selection_name: str = ContextField(
        description="Selection chosen by the player",
        index="text",
    )

    odds_decimal: float = ContextField(
        description="Accepted decimal odds",
        index="numeric",
    )

    leg_status: str = ContextField(
        description="Leg status: open, won, lost, void, pending",
        index="tag",
    )

    result_detail: str | None = ContextField(
        description="Result explanation for the leg",
        index="text",
    )

    bet: Any = ContextRelationship(
        description="Parent bet",
        target="Bet",
        source_field="bet_id",
    )

    event: Any = ContextRelationship(
        description="Related event",
        target="SportEvent",
        source_field="event_id",
    )

    market: Any = ContextRelationship(
        description="Related market",
        target="Market",
        source_field="market_id",
    )


class BetSettlementEvent(ContextModel):
    """BetSettlementEvent entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_settlement_event:{settlement_event_id}"

    settlement_event_id: str = ContextField(
        description="Unique settlement timeline event identifier",
        is_key_component=True,
    )

    bet_id: str = ContextField(
        description="Associated bet",
        index="tag",
    )

    event_type: str = ContextField(
        description="Timeline event type: placed, event_final, result_received, review_started, bet_settled, payout_credited",
        index="tag",
    )

    timestamp: str = ContextField(
        description="ISO timestamp of the event",
    )

    description: str = ContextField(
        description="Human-readable settlement event description",
        index="text",
    )

    actor: str = ContextField(
        description="Who triggered it: player, trading, feed, system, support",
        index="tag",
    )

    bet: Any = ContextRelationship(
        description="Associated bet",
        target="Bet",
        source_field="bet_id",
    )


class WalletTransaction(ContextModel):
    """WalletTransaction entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_wallet_transaction:{transaction_id}"

    transaction_id: str = ContextField(
        description="Unique wallet transaction identifier",
        is_key_component=True,
    )

    player_id: str = ContextField(
        description="Player who owns the wallet transaction",
        index="tag",
    )

    bet_id: str | None = ContextField(
        description="Related bet when applicable",
        index="tag",
    )

    transaction_type: str = ContextField(
        description="Transaction type: deposit, stake, payout, refund, withdrawal",
        index="tag",
    )

    amount: float = ContextField(
        description="Signed transaction amount",
        index="numeric",
        sortable=True,
    )

    balance_after: float = ContextField(
        description="Wallet balance after the transaction",
        index="numeric",
        sortable=True,
    )

    status: str = ContextField(
        description="Transaction status: pending, completed, failed, held",
        index="tag",
    )

    created_at: str = ContextField(
        description="ISO timestamp of transaction creation",
    )

    payment_method: str | None = ContextField(
        description="Payment method or wallet rail",
        index="tag",
    )

    processor_reference: str | None = ContextField(
        description="Processor or ledger reference",
        index="tag",
    )

    player: Any = ContextRelationship(
        description="Player who owns the transaction",
        target="Player",
        source_field="player_id",
    )

    bet: Any = ContextRelationship(
        description="Related bet",
        target="Bet",
        source_field="bet_id",
    )


class SupportTicket(ContextModel):
    """SupportTicket entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_support_ticket:{ticket_id}"

    ticket_id: str = ContextField(
        description="Unique support ticket identifier",
        is_key_component=True,
    )

    player_id: str = ContextField(
        description="Player who filed the ticket",
        index="tag",
    )

    bet_id: str | None = ContextField(
        description="Related bet",
        index="tag",
    )

    category: str = ContextField(
        description="Category: settlement_delay, cashout, account, payment, responsible_gaming",
        index="tag",
    )

    status: str = ContextField(
        description="Ticket status: open, in_progress, resolved, closed",
        index="tag",
    )

    created_at: str = ContextField(
        description="ISO timestamp when ticket was created",
    )

    resolved_at: str | None = ContextField(
        description="ISO timestamp when resolved",
    )

    summary: str = ContextField(
        description="Ticket summary",
        index="text",
    )

    resolution: str | None = ContextField(
        description="How it was resolved",
    )

    player: Any = ContextRelationship(
        description="Player who filed the ticket",
        target="Player",
        source_field="player_id",
    )

    bet: Any = ContextRelationship(
        description="Related bet",
        target="Bet",
        source_field="bet_id",
    )


class Policy(ContextModel):
    """Policy entity for the Sports Desk domain."""

    __redis_key_template__ = "sports_betting_policy:{policy_id}"

    policy_id: str = ContextField(
        description="Unique policy identifier",
        is_key_component=True,
    )

    title: str = ContextField(
        description="Policy title",
        index="text",
        weight=2.0,
    )

    category: str = ContextField(
        description="Policy category",
        index="tag",
    )

    content: str = ContextField(
        description="Full policy text",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Vector embedding of policy content",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
