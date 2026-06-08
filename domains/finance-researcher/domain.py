from __future__ import annotations

import json
import importlib.util
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any, Sequence

from backend.app.core.domain_contract import (
    BrandingConfig,
    DomainManifest,
    GeneratedDataset,
    GuardrailConfig,
    GuardrailRouteConfig,
    IdentityConfig,
    InternalToolDefinition,
    NamespaceConfig,
    PromptCard,
    RagConfig,
    SeedLangCacheEntry,
    SeedMemory,
    ThemeConfig,
    UiConfig,
)
from backend.app.core.domain_schema import EntitySpec, validate_entity_specs
from backend.app.domain_events import build_domain_event, publish_domain_event
from backend.app.memory_service import MemoryService
from backend.app.redis_connection import create_redis_client

ROOT = Path(__file__).resolve().parents[2]


def _load_local_module(module_name: str, file_name: str):
    module_path = Path(__file__).resolve().parent / file_name
    spec = importlib.util.spec_from_file_location(f"finance_researcher_{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load finance-researcher module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_data_generator = _load_local_module("data_generator", "data_generator.py")
_prompt = _load_local_module("prompt", "prompt.py")
_schema = _load_local_module("schema", "schema.py")

generate_demo_data = _data_generator.generate_demo_data
build_system_prompt = _prompt.build_system_prompt
ENTITY_SPECS = _schema.ENTITY_SPECS


WATCHLIST = (
    ("NVDA", "NVIDIA"),
    ("AMD", "Advanced Micro Devices"),
    ("AVGO", "Broadcom"),
    ("MU", "Micron Technology"),
    ("INTC", "Intel"),
    ("QCOM", "Qualcomm"),
    ("AAPL", "Apple"),
    ("AMZN", "Amazon"),
    ("MSFT", "Microsoft"),
    ("GOOGL", "Alphabet"),
    ("META", "Meta Platforms"),
    ("TSLA", "Tesla"),
    ("ORCL", "Oracle"),
    ("MDB", "MongoDB"),
)

WATCHLIST_DETAILS = tuple(getattr(_data_generator, "WATCHLIST", []))
WATCHLIST_BY_TICKER = {entry["ticker"].upper(): entry for entry in WATCHLIST_DETAILS}
PRICE_TIMESERIES_FIELDS = {
    "close": {"source_field": "close", "unit": "USD", "label": "Close price"},
    "volume": {"source_field": "volume", "unit": "shares", "label": "Volume"},
}
TIMESERIES_WINDOWS = {
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "1y": 365,
    "3y": 365 * 3,
    "max": None,
}
TIMESERIES_DEFAULT_LIMIT = 24


def _price_timeseries_key(*, redis_prefix: str, ticker: str, series_name: str) -> str:
    return f"{redis_prefix}:ts:price:{ticker.lower()}:{series_name}"


def _metric_timeseries_key(*, redis_prefix: str, ticker: str, metric_name: str, period_type: str) -> str:
    return f"{redis_prefix}:ts:metric:{ticker.lower()}:{period_type.lower()}:{metric_name}"


def _iso_date_to_epoch_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return int(parsed.timestamp() * 1000)


def _epoch_ms_to_iso_date(value: int | float | str) -> str:
    timestamp = int(float(value))
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()


def _flatten_labels(labels: dict[str, str]) -> list[str]:
    flattened: list[str] = []
    for key, value in labels.items():
        flattened.extend([key, _sanitize_label_value(value)])
    return flattened


def _sanitize_label_value(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "unknown"
    return re.sub(r"[^A-Za-z0-9:_-]+", "_", text)


def _downsample_points(points: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or len(points) <= limit:
        return points
    if limit == 1:
        return [points[-1]]

    step = (len(points) - 1) / (limit - 1)
    sampled: list[dict[str, Any]] = []
    used_indexes: set[int] = set()
    for sample_index in range(limit):
        point_index = int(round(sample_index * step))
        point_index = max(0, min(point_index, len(points) - 1))
        if point_index in used_indexes:
            continue
        used_indexes.add(point_index)
        sampled.append(points[point_index])
    if sampled[-1] != points[-1]:
        sampled[-1] = points[-1]
    return sampled


def _parse_tickers(raw: str | None) -> list[str]:
    if not raw:
        return []
    normalized = raw.replace(",", " ").split()
    seen: set[str] = set()
    result: list[str] = []
    for token in normalized:
        ticker = token.strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        result.append(ticker)
    return result


def _timeseries_window_bounds(window: str) -> tuple[str | int, str | int, str]:
    normalized = window if window in TIMESERIES_WINDOWS else "1y"
    days = TIMESERIES_WINDOWS[normalized]
    if days is None:
        return "-", "+", normalized
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return int(start.timestamp() * 1000), int(now.timestamp() * 1000), normalized


def _timeseries_series_metadata(
    *,
    redis_prefix: str,
    ticker: str,
    series_name: str,
    period_type: str,
) -> dict[str, str]:
    company = WATCHLIST_BY_TICKER[ticker]
    if series_name in PRICE_TIMESERIES_FIELDS:
        config = PRICE_TIMESERIES_FIELDS[series_name]
        return {
            "key": _price_timeseries_key(redis_prefix=redis_prefix, ticker=ticker, series_name=series_name),
            "series_family": "price",
            "label": f"{ticker} {config['label']}",
            "unit": config["unit"],
            "company_name": company["company_name"],
        }
    unit = "USD" if series_name != "diluted_eps" else "USD/shares"
    return {
        "key": _metric_timeseries_key(
            redis_prefix=redis_prefix,
            ticker=ticker,
            metric_name=series_name,
            period_type=period_type,
        ),
        "series_family": "metric",
        "label": f"{ticker} {series_name.replace('_', ' ')}",
        "unit": unit,
        "company_name": company["company_name"],
    }


def _write_finance_timeseries(*, client: Any, redis_prefix: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    price_rows = records.get("PriceBar", [])
    metric_rows = records.get("FinancialMetricPoint", [])

    key_labels: dict[str, dict[str, str]] = {}
    for row in price_rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker not in WATCHLIST_BY_TICKER:
            continue
        company = WATCHLIST_BY_TICKER[ticker]
        for series_name, config in PRICE_TIMESERIES_FIELDS.items():
            key = _price_timeseries_key(redis_prefix=redis_prefix, ticker=ticker, series_name=series_name)
            key_labels[key] = {
                "domain": "finance-researcher",
                "ticker": ticker,
                "company_name": company["company_name"],
                "series_family": "price",
                "series_name": series_name,
                "unit": config["unit"],
            }

    for row in metric_rows:
        ticker = str(row.get("ticker", "")).upper()
        metric_name = str(row.get("metric_name", "")).strip()
        period_type = str(row.get("period_type", "quarter")).strip().lower() or "quarter"
        if ticker not in WATCHLIST_BY_TICKER or not metric_name:
            continue
        company = WATCHLIST_BY_TICKER[ticker]
        unit = str(row.get("currency") or row.get("unit") or "")
        key = _metric_timeseries_key(
            redis_prefix=redis_prefix,
            ticker=ticker,
            metric_name=metric_name,
            period_type=period_type,
        )
        key_labels[key] = {
            "domain": "finance-researcher",
            "ticker": ticker,
            "company_name": company["company_name"],
            "series_family": "metric",
            "series_name": metric_name,
            "period_type": period_type,
            "unit": unit or "value",
        }

    keys_to_reset = sorted(key_labels)
    if keys_to_reset:
        client.delete(*keys_to_reset)

    create_pipe = client.pipeline(transaction=False)
    for key in keys_to_reset:
        create_pipe.execute_command(
            "TS.CREATE",
            key,
            "RETENTION",
            0,
            "DUPLICATE_POLICY",
            "LAST",
            "LABELS",
            *_flatten_labels(key_labels[key]),
        )
    if keys_to_reset:
        create_pipe.execute()

    add_pipe = client.pipeline(transaction=False)
    buffered = 0
    point_count = 0
    for row in sorted(price_rows, key=lambda entry: (entry.get("ticker", ""), entry.get("trade_date", ""))):
        ticker = str(row.get("ticker", "")).upper()
        if ticker not in WATCHLIST_BY_TICKER:
            continue
        timestamp_ms = _iso_date_to_epoch_ms(str(row["trade_date"]))
        for series_name, config in PRICE_TIMESERIES_FIELDS.items():
            add_pipe.execute_command(
                "TS.ADD",
                _price_timeseries_key(redis_prefix=redis_prefix, ticker=ticker, series_name=series_name),
                timestamp_ms,
                row[config["source_field"]],
            )
            buffered += 1
            point_count += 1
            if buffered >= 1000:
                add_pipe.execute()
                buffered = 0

    for row in sorted(metric_rows, key=lambda entry: (entry.get("ticker", ""), entry.get("metric_name", ""), entry.get("period_end", ""))):
        ticker = str(row.get("ticker", "")).upper()
        metric_name = str(row.get("metric_name", "")).strip()
        period_type = str(row.get("period_type", "quarter")).strip().lower() or "quarter"
        if ticker not in WATCHLIST_BY_TICKER or not metric_name:
            continue
        timestamp_ms = _iso_date_to_epoch_ms(str(row["period_end"]))
        add_pipe.execute_command(
            "TS.ADD",
            _metric_timeseries_key(
                redis_prefix=redis_prefix,
                ticker=ticker,
                metric_name=metric_name,
                period_type=period_type,
            ),
            timestamp_ms,
            row["value"],
        )
        buffered += 1
        point_count += 1
        if buffered >= 1000:
            add_pipe.execute()
            buffered = 0

    if buffered > 0:
        add_pipe.execute()

    metric_series_count = sum(1 for labels in key_labels.values() if labels.get("series_family") == "metric")
    price_series_count = sum(1 for labels in key_labels.values() if labels.get("series_family") == "price")
    return {
        "enabled": True,
        "series_count": len(key_labels),
        "price_series_count": price_series_count,
        "metric_series_count": metric_series_count,
        "point_count": point_count,
        "available_metric_series": sorted(
            {
                str(row.get("metric_name", "")).strip()
                for row in metric_rows
                if str(row.get("metric_name", "")).strip()
            }
        ),
        "available_price_series": sorted(PRICE_TIMESERIES_FIELDS),
    }


class FinanceResearcherDomain:
    manifest = DomainManifest(
        id="finance-researcher",
        description=(
            "Finance research demo domain for watchlist analysis across filings, earnings materials, metrics, prices, "
            "and normalized update events."
        ),
        generated_models_module="domains.finance-researcher.generated_models",
        generated_models_path="domains/finance-researcher/generated_models.py",
        output_dir="output/finance-researcher",
        branding=BrandingConfig(
            app_name="ShiftIQ",
            subtitle="Market shifts, made clear.",
            hero_title="Finance Research Assistant",
            placeholder_text="Compare companies, documents, metrics, or recent events...",
            logo_path="domains/finance-researcher/assets/logo.svg",
            demo_steps=[
                "Compare the latest gross profit trends for NVIDIA, AMD, and Broadcom",
                "Remember that I focus on semiconductor stocks and prefer quarterly earnings data",
                "Click Memory",
                "Given what you know about my research focus, what should I look at next across my watchlist?",
            ],
            starter_prompts=[
                PromptCard(
                    eyebrow="Context",
                    title="Walk me through Oracle",
                    prompt="Walk me through Oracle's latest quarter using both the filing and the structured metrics.",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Save research preferences",
                    prompt="Please remember that I prefer visual comparisons with charts when analyzing multi-company trends.",
                ),
                PromptCard(
                    eyebrow="Memory",
                    title="Coverage and preferences",
                    prompt="What is my semiconductor coverage and analysis preferences?",
                ),
                PromptCard(
                    eyebrow="Cached",
                    title="Gross profit trends",
                    prompt="Compare the latest gross profit trends for NVIDIA, AMD, and Broadcom",
                ),
            ],
            theme=ThemeConfig(
                bg="#081018",
                bg_accent_a="rgba(39, 145, 255, 0.18)",
                bg_accent_b="rgba(51, 214, 164, 0.10)",
                panel="rgba(12, 19, 29, 0.90)",
                panel_strong="rgba(9, 15, 24, 0.96)",
                panel_elevated="rgba(16, 26, 38, 0.94)",
                line="rgba(75, 173, 255, 0.14)",
                line_strong="rgba(75, 173, 255, 0.25)",
                text="#eef4fb",
                muted="#9fb0c2",
                soft="#d2deeb",
                accent="#6fd3ff",
                user="#13263a",
                landing_bg="#F3F4F1",
            ),
            ui=UiConfig(
                show_platform_surface=True,
                show_live_updates=True,
                platform_surface_title="Context Surfaces, RedisTimeSeries, and Redis Streams in one demo",
                platform_data_planes=["Context Surfaces", "RedisTimeSeries", "Redis Streams"],
                live_updates_title="Redis Stream feed for Finance Researcher",
            ),
        ),
        namespace=NamespaceConfig(
            redis_prefix="finance-researcher",
            dataset_meta_key="finance-researcher:meta:dataset",
            checkpoint_prefix="finance-researcher:checkpoint",
            checkpoint_write_prefix="finance-researcher:checkpoint_write",
            redis_instance_name="Finance Researcher Redis Cloud",
            surface_name="Finance Researcher Surface",
            agent_name="Finance Researcher Agent",
        ),
        rag=RagConfig(
            tool_name="vector_search_research_chunks",
            status_text="Searching research chunks…",
            generating_text="Generating answer…",
            index_name_contains="researchchunk",
            vector_field="content_embedding",
            return_fields=["company_id", "ticker", "document_id", "section_heading", "page_label", "chunk_text"],
            title_fields=["section_heading", "headline", "document_id"],
            label_fields=["ticker", "page_label", "company_id"],
            body_fields=["chunk_text", "content", "summary", "description", "text"],
            num_results=3,
            answer_system_prompt=(
                "Answer using only the provided research chunks and structured finance records. "
                "Separate facts from narrative evidence, name the company and period explicitly, and say when the "
                "available data does not support a claim."
            ),
        ),
        identity=IdentityConfig(
            default_id="ANALYST_DEMO_001",
            default_name="Morgan Lee",
            default_email="morgan.lee@example.com",
            description=(
                "Returns the signed-in analyst profile used for the finance-researcher demo, including the active "
                "watchlist context."
            ),
        ),
        guardrail=GuardrailConfig(
            router_name="shiftiq-guardrails",
            allowed_route_name="financial_research",
            routes=[
                GuardrailRouteConfig(
                    name="financial_research",
                    references=[
                        "Compare the latest NVIDIA and AMD filings",
                        "What changed in Broadcom's earnings this quarter?",
                        "Show me NVDA gross profit trends",
                        "Pull the SEC filing for Microsoft",
                        "How does Oracle's revenue compare to its peers?",
                        "What's the operating margin trend for AMD?",
                        "Walk me through Intel's latest quarterly earnings",
                        "What's new on my watchlist?",
                        "Compare stock price trends for NVDA and AVGO",
                        "Show me the revenue breakdown for Meta",
                        "What did management say about AI revenue in the latest filing?",
                        "How has diluted EPS trended for Tesla over the past year?",
                        "Filter coverage events for Qualcomm",
                        "Update my watchlist research notes",
                        "What are the key differences between NVIDIA and AMD this quarter?",
                        "Show me Micron's net income trend",
                        "Which semiconductor company had the best gross profit growth?",
                        "Summarize the latest Amazon earnings document",
                        "Compare sector fundamentals across my watchlist",
                        "What's the latest filing date for Alphabet?",
                        "Yes",
                        "No",
                        "Tell me more",
                        "Go ahead",
                        "Sure",
                        "Thanks",
                        "Hello",
                        "Can you help me?",
                    ],
                    distance_threshold=0.7,
                ),
                GuardrailRouteConfig(
                    name="off_topic",
                    references=[
                        "What's the weather like today?",
                        "Tell me a joke",
                        "Write me a Python script",
                        "Help me with a cooking recipe",
                        "Who won the game last night?",
                        "Should I buy this stock?",
                        "Give me crypto trading tips",
                        "What's the best savings account rate?",
                        "Help me with my personal budget",
                        "Explain quantum physics",
                        "Translate this to French",
                        "Write a poem",
                        "What's the capital of Japan?",
                        "Generate an image of a chart",
                        "How do I fix my car?",
                    ],
                    distance_threshold=0.5,
                ),
            ],
        ),
        seed_memories=[
            SeedMemory(
                text="Focuses on semiconductor sector — NVDA, AMD, AVGO are primary coverage",
                topics=["watchlist", "preferences"],
            ),
            SeedMemory(
                text="Prefers quarterly earnings over annual filings for recent momentum analysis",
                topics=["research", "methodology"],
            ),
        ],
        seed_langcache=[
            SeedLangCacheEntry(
                prompt="Compare the latest gross profit trends for NVIDIA, AMD, and Broadcom",
                response=(
                    "Based on the most recent quarterly filings:\n\n"
                    "- **NVIDIA (NVDA)**: Gross profit continues to accelerate, driven by AI accelerator demand. "
                    "Quarter-over-quarter growth remains the strongest among semiconductor peers.\n"
                    "- **AMD**: Gross profit has been relatively flat, reflecting competitive pressure in both CPU "
                    "and GPU segments.\n"
                    "- **Broadcom (AVGO)**: Steady gross profit growth driven by infrastructure and networking demand.\n\n"
                    "For detailed numbers, I can pull the exact quarterly metrics from the research database."
                ),
                attributes={"domain": "finance-researcher"},
            ),
        ],
    )

    def get_entity_specs(self) -> tuple[EntitySpec, ...]:
        return ENTITY_SPECS

    def get_runtime_config(self, *, settings: Any) -> dict[str, Any]:
        memory_enabled = MemoryService(settings).is_configured() if settings else False
        return {
            "watchlist_size": len(WATCHLIST),
            "memory_enabled": memory_enabled,
        }

    def build_system_prompt(
        self,
        *,
        mcp_tools: Sequence[dict[str, Any]],
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        return build_system_prompt(
            mcp_tools=mcp_tools,
            runtime_config=runtime_config,
            memory_enabled=bool((runtime_config or {}).get("memory_enabled")),
        )

    def build_answer_verifier_prompt(self, *, runtime_config: dict[str, Any] | None = None) -> str:
        del runtime_config
        return (
            "When the user says 'it', 'that quarter', or 'recent', resolve the exact company, ticker, document, and "
            "period before answering. Keep structured metrics separate from narrative evidence unless both are "
            "explicitly tied to the same company and period."
        )

    def describe_tool_trace_step(
        self,
        *,
        tool_name: str,
        payload: Any,
        runtime_config: dict[str, Any] | None = None,
    ) -> str | None:
        del runtime_config
        detail = ""
        if isinstance(payload, dict):
            for key in ("query", "text", "ticker", "company_id", "document_id", "metric_name", "event_type"):
                value = payload.get(key)
                if value:
                    detail = str(value)
                    break

        if tool_name == self.manifest.identity.tool_name:
            return "Identify the signed-in analyst and use their watchlist as the default research context."
        if tool_name == "get_current_time":
            return "Anchor comparisons to the current market and filing calendar."
        if tool_name == "dataset_overview":
            return "Inspect the current research dataset coverage before answering."
        if tool_name == "watchlist_overview":
            return "Review the analyst's 14-company watchlist and the current coverage state."
        if tool_name == "query_finance_timeseries":
            if detail:
                return f"Query RedisTimeSeries for finance trend data: {detail}."
            return "Query RedisTimeSeries for finance trend data and inspect the exact command output."
        if tool_name == "vector_search_research_chunks":
            return f"Search the research corpus for narrative evidence: {detail or 'research query'}."
        if tool_name == "search_analyst_memory":
            return "Search durable analyst memory for research preferences, coverage focus, or stored context."
        if tool_name == "remember_analyst_preference":
            return "Store a durable analyst preference or research note for future sessions."
        return None

    def get_internal_tool_definitions(
        self,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Sequence[InternalToolDefinition]:
        tools: list[InternalToolDefinition] = [
            InternalToolDefinition(
                name=self.manifest.identity.tool_name,
                description=self.manifest.identity.description,
            ),
            InternalToolDefinition(
                name="get_current_time",
                description="Returns the current UTC date and time in ISO 8601 format for recency and period comparisons.",
            ),
            InternalToolDefinition(
                name="dataset_overview",
                description=(
                    "Returns a summary of the finance-researcher dataset, including company, document, chunk, metric, "
                    "price, and event counts."
                ),
            ),
            InternalToolDefinition(
                name="watchlist_overview",
                description="Returns the 14-company analyst watchlist and the latest known coverage state for each company.",
            ),
            InternalToolDefinition(
                name="query_finance_timeseries",
                description=(
                    "Query RedisTimeSeries for one or more finance watchlist tickers and return the exact TS.RANGE "
                    "commands, sampled results, and chart-ready trend data."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "tickers": {
                            "type": "string",
                            "description": "Comma-separated watchlist tickers like NVDA, AMD, or MSFT.",
                        },
                        "series_name": {
                            "type": "string",
                            "description": (
                                "Series to query: close, volume, revenue, gross_profit, operating_income, "
                                "net_income, diluted_eps, or another loaded FinancialMetricPoint.metric_name."
                            ),
                            "default": "close",
                        },
                        "period_type": {
                            "type": "string",
                            "description": "For financial metrics, the period type to read from RedisTimeSeries.",
                            "default": "quarter",
                        },
                        "window": {
                            "type": "string",
                            "description": "Recent window: 30d, 90d, 180d, 1y, 3y, or max.",
                            "default": "1y",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum points per returned series after client-side sampling.",
                            "default": TIMESERIES_DEFAULT_LIMIT,
                        },
                    },
                    "required": ["tickers"],
                },
            ),
        ]
        if (runtime_config or {}).get("memory_enabled"):
            tools.extend(
                [
                    InternalToolDefinition(
                        name="search_analyst_memory",
                        description=(
                            "Search durable analyst memory for research preferences, coverage focus, methodology notes, "
                            "or facts from previous sessions. Use this when the user asks what you remember, refers to "
                            "preferences, or wants continuity across conversations."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "What to look up in analyst memory."},
                                "limit": {"type": "integer", "description": "Optional max number of memories to return.", "default": 5},
                            },
                            "required": ["query"],
                        },
                    ),
                    InternalToolDefinition(
                        name="remember_analyst_preference",
                        description=(
                            "Save a durable analyst preference or research note into long-term memory. "
                            "Only use this when the user explicitly asks you to remember something or states a lasting preference."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "The exact analyst preference or research note to remember."},
                                "memory_type": {
                                    "type": "string",
                                    "description": "Memory type: semantic for preferences/facts, episodic for a notable event, message for a verbatim note.",
                                    "default": "semantic",
                                },
                                "topics": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Optional topic tags like watchlist, research, methodology, sector, preferences.",
                                },
                            },
                            "required": ["text"],
                        },
                    ),
                ]
            )
        return tuple(tools)

    def execute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name == self.manifest.identity.tool_name:
            identity = self.manifest.identity
            return {
                identity.id_field: os.getenv(identity.id_env_var, identity.default_id),
                "name": os.getenv(identity.name_env_var, identity.default_name),
                "email": os.getenv(identity.email_env_var, identity.default_email),
                "watchlist_size": len(WATCHLIST),
            }
        if tool_name == "get_current_time":
            now = datetime.now(timezone.utc)
            return {"current_time": now.isoformat(), "timezone": "UTC"}
        if tool_name == "dataset_overview":
            client = create_redis_client(settings)
            raw = client.execute_command("JSON.GET", self.manifest.namespace.dataset_meta_key, "$")
            if raw:
                data = json.loads(raw)
                return data[0] if isinstance(data, list) else data
            return {"error": "Dataset metadata not found. Run the data loader first."}
        if tool_name == "watchlist_overview":
            return {
                "watchlist_size": len(WATCHLIST),
                "watchlist": [{"ticker": ticker, "company_name": company_name} for ticker, company_name in WATCHLIST],
            }
        if tool_name == "query_finance_timeseries":
            tickers = _parse_tickers(str(arguments.get("tickers") or ""))
            if not tickers:
                return {"error": "Provide at least one watchlist ticker via the 'tickers' argument."}

            invalid = [ticker for ticker in tickers if ticker not in WATCHLIST_BY_TICKER]
            if invalid:
                return {
                    "error": "One or more tickers are not in the 14-company watchlist.",
                    "invalid_tickers": invalid,
                    "watchlist": sorted(WATCHLIST_BY_TICKER),
                }

            series_name = str(arguments.get("series_name") or "close").strip().lower()
            period_type = str(arguments.get("period_type") or "quarter").strip().lower() or "quarter"
            limit = max(4, min(int(arguments.get("limit") or TIMESERIES_DEFAULT_LIMIT), 60))
            from_ts, to_ts, normalized_window = _timeseries_window_bounds(str(arguments.get("window") or "1y").strip())

            client = create_redis_client(settings)
            series_results: list[dict[str, Any]] = []
            redis_commands: list[str] = []
            total_point_count = 0
            family = "price" if series_name in PRICE_TIMESERIES_FIELDS else "metric"
            for ticker in tickers:
                metadata = _timeseries_series_metadata(
                    redis_prefix=self.manifest.namespace.redis_prefix,
                    ticker=ticker,
                    series_name=series_name,
                    period_type=period_type,
                )
                redis_command = f"TS.RANGE {metadata['key']} {from_ts} {to_ts}"
                redis_commands.append(redis_command)
                try:
                    raw_points = client.execute_command("TS.RANGE", metadata["key"], from_ts, to_ts)
                except Exception as exc:
                    return {
                        "error": "RedisTimeSeries query failed.",
                        "redis_command": redis_command,
                        "detail": str(exc),
                    }

                points = [
                    {
                        "date": _epoch_ms_to_iso_date(timestamp),
                        "ts": int(float(timestamp)),
                        "value": float(value),
                    }
                    for timestamp, value in raw_points or []
                ]
                total_point_count += len(points)
                sampled_points = _downsample_points(points, limit)
                company = WATCHLIST_BY_TICKER[ticker]
                series_results.append(
                    {
                        "ticker": ticker,
                        "company_name": company["company_name"],
                        "series_name": series_name,
                        "series_family": family,
                        "period_type": period_type if family == "metric" else None,
                        "redis_key": metadata["key"],
                        "unit": metadata["unit"],
                        "point_count": len(points),
                        "sampled_point_count": len(sampled_points),
                        "points": sampled_points,
                    }
                )

            return {
                "timeseries_used": True,
                "series_family": family,
                "series_name": series_name,
                "window": normalized_window,
                "period_type": period_type if family == "metric" else None,
                "requested_tickers": tickers,
                "redis_commands": redis_commands,
                "summary": {
                    "series_count": len(series_results),
                    "raw_point_count": total_point_count,
                    "sampled_point_limit": limit,
                },
                "chart": {
                    "type": "timeseries",
                    "chart_style": "line",
                    "title": (
                        f"{series_name.replace('_', ' ').title()} trend"
                        if family == "metric"
                        else f"{series_name.title()} trend"
                    ),
                    "subtitle": (
                        f"{normalized_window} window across {len(series_results)} ticker"
                        f"{'' if len(series_results) == 1 else 's'}"
                    ),
                    "unit": series_results[0]["unit"] if series_results else "",
                    "series": [
                        {
                            "label": f"{entry['ticker']} {series_name.replace('_', ' ')}",
                            "ticker": entry["ticker"],
                            "unit": entry["unit"],
                            "points": entry["points"],
                        }
                        for entry in series_results
                    ],
                },
                "series": series_results,
            }
        return {"error": f"Unknown tool: {tool_name}"}

    async def aexecute_internal_tool(self, tool_name: str, arguments: dict[str, Any], settings: Any) -> dict[str, Any]:
        if tool_name not in {"search_analyst_memory", "remember_analyst_preference"}:
            return self.execute_internal_tool(tool_name, arguments, settings)

        identity = self.manifest.identity
        owner_id = os.getenv(identity.id_env_var, identity.default_id)
        memory_service = MemoryService(settings)
        if not memory_service.is_configured():
            return {"error": "Memory service is not configured for this demo."}

        if tool_name == "search_analyst_memory":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return {"error": "query is required"}
            limit = arguments.get("limit")
            memories = await memory_service.asearch_long_term_memory(
                text=query,
                owner_id=owner_id,
                limit=int(limit) if limit is not None else None,
            )
            return {
                "owner_id": owner_id,
                "query": query,
                "memory_count": len(memories),
                "memories": [
                    {
                        "id": memory.get("id"),
                        "text": memory.get("text"),
                        "memory_type": memory.get("memoryType"),
                        "topics": memory.get("topics", []),
                        "session_id": memory.get("sessionId"),
                        "created_at": memory.get("createdAt"),
                    }
                    for memory in memories
                ],
            }

        # remember_analyst_preference — blocked in demo mode
        text = str(arguments.get("text", "")).strip()
        if not text:
            return {"error": "text is required"}
        memory_type = str(arguments.get("memory_type", "semantic")).strip() or "semantic"
        if memory_type not in {"semantic", "episodic", "message"}:
            memory_type = "semantic"
        topics = arguments.get("topics") or []
        if not isinstance(topics, list):
            topics = []
        return {
            "owner_id": owner_id,
            "saved_text": text,
            "memory_type": memory_type,
            "topics": [str(t).strip() for t in topics if str(t).strip()],
            "demo_blocked": True,
            "response": {"acknowledged": True},
        }

    def publish_coverage_event(
        self,
        *,
        settings: Any,
        company_id: str,
        ticker: str,
        headline: str,
        event_type: str,
        message: str = "",
        source: str = "domain-refresh",
        document_id: str = "",
        importance_score: float | int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        event = build_domain_event(
            event_family="coverage",
            event_type=event_type,
            headline=headline,
            message=message,
            source=source,
            company_id=company_id,
            ticker=ticker,
            document_id=document_id,
            importance_score=importance_score,
            payload=payload,
        )
        return publish_domain_event(settings, self, event)

    def write_dataset_meta(self, *, settings: Any, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        timeseries_summary: dict[str, Any]
        client = create_redis_client(settings)
        try:
            timeseries_summary = _write_finance_timeseries(
                client=client,
                redis_prefix=self.manifest.namespace.redis_prefix,
                records=records,
            )
        except Exception as exc:
            timeseries_summary = {
                "enabled": False,
                "error": str(exc),
                "series_count": 0,
                "point_count": 0,
                "price_series_count": 0,
                "metric_series_count": 0,
                "available_metric_series": [],
                "available_price_series": sorted(PRICE_TIMESERIES_FIELDS),
            }
        summary = {
            "analyst_profiles": len(records.get("AnalystProfile", [])),
            "companies": len(records.get("Company", [])),
            "research_documents": len(records.get("ResearchDocument", [])),
            "research_chunks": len(records.get("ResearchChunk", [])),
            "financial_metric_points": len(records.get("FinancialMetricPoint", [])),
            "price_bars": len(records.get("PriceBar", [])),
            "coverage_events": len(records.get("CoverageEvent", [])),
            "company_count": len(records.get("Company", [])),
            "document_count": len(records.get("ResearchDocument", [])),
            "chunk_count": len(records.get("ResearchChunk", [])),
            "metric_point_count": len(records.get("FinancialMetricPoint", [])),
            "price_bar_count": len(records.get("PriceBar", [])),
            "coverage_event_count": len(records.get("CoverageEvent", [])),
            "timeseries_enabled": timeseries_summary["enabled"],
            "timeseries_series_count": timeseries_summary["series_count"],
            "timeseries_point_count": timeseries_summary["point_count"],
            "timeseries_price_series_count": timeseries_summary["price_series_count"],
            "timeseries_metric_series_count": timeseries_summary["metric_series_count"],
            "timeseries_available_metric_series": timeseries_summary["available_metric_series"],
            "timeseries_available_price_series": timeseries_summary["available_price_series"],
        }
        if not timeseries_summary["enabled"] and timeseries_summary.get("error"):
            summary["timeseries_error"] = timeseries_summary["error"]
        client.execute_command(
            "JSON.SET",
            self.manifest.namespace.dataset_meta_key,
            "$",
            json.dumps(summary, ensure_ascii=False),
        )
        return summary

    def generate_demo_data(
        self,
        *,
        output_dir: Path,
        seed: int | None = None,
        update_env_file: bool = False,
    ) -> GeneratedDataset:
        return generate_demo_data(output_dir=output_dir, seed=seed, update_env_file=update_env_file)

    def validate(self) -> list[str]:
        errors = validate_entity_specs(self.get_entity_specs())
        if not (ROOT / self.manifest.branding.logo_path).exists():
            errors.append(f"Logo file not found: {self.manifest.branding.logo_path}")
        if not self.manifest.branding.starter_prompts:
            errors.append("Branding must define at least one starter prompt")
        return errors


DOMAIN = FinanceResearcherDomain()
