import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ChatRole = "user" | "assistant";

type ToolEvent = {
  runId: string;
  toolName: string;
  toolKind: "internal_function" | "mcp_tool" | "cache";
  status: "call" | "result";
  payload: Record<string, unknown>;
  durationMs?: number;
  ts?: number;
};

type MergedToolEvent = {
  runId: string;
  toolName: string;
  toolKind: ToolEvent["toolKind"];
  callPayload?: Record<string, unknown>;
  resultPayload?: Record<string, unknown>;
  durationMs?: number;
  ts?: number;
};

type ThinkingStep = {
  id: string;
  text: string;
  ts: number;
  kind: "plan" | "llm";
  durationMs?: number;
  durationText?: string;
};

type StatusMessage = { text: string; ts: number };

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  statusMessages: StatusMessage[];
  thinkingSteps: ThinkingStep[];
  toolEvents: ToolEvent[];
  totalElapsedMs?: number;
};

type HealthState = {
  ok: boolean;
  domain: string;
  mcp_enabled: boolean;
  internal_tools: string[];
  mcp_tools: string[];
} | null;

type AgentMode = "context_surfaces" | "simple_rag";

type PromptCard = { eyebrow: string; title: string; prompt: string };
type DemoUserOption = { id: string; label: string; subtitle?: string | null; cache_group_id?: string | null };

type DomainConfig = {
  id: string;
  app_name: string;
  subtitle: string;
  hero_title: string;
  placeholder_text: string;
  starter_prompts: PromptCard[];
  theme: Record<string, string>;
  ui?: {
    show_platform_surface?: boolean;
    show_live_updates?: boolean;
    platform_surface_eyebrow?: string;
    platform_surface_title?: string;
    platform_data_planes?: string[];
    live_updates_eyebrow?: string;
    live_updates_title?: string;
  };
  logo_src: string;
  semantic_cache_enabled?: boolean;
  demo_users?: DemoUserOption[];
  default_demo_user_id?: string | null;
} | null;

function isLightColor(value?: string) {
  if (!value) return false;
  const hex = value.trim();
  const match = hex.match(/^#([0-9a-fA-F]{6})$/);
  if (!match) return false;
  const raw = match[1];
  const r = Number.parseInt(raw.slice(0, 2), 16);
  const g = Number.parseInt(raw.slice(2, 4), 16);
  const b = Number.parseInt(raw.slice(4, 6), 16);
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luminance > 0.72;
}

type DomainEvent = {
  stream_id: string;
  event_family: string;
  event_type: string;
  headline: string;
  message?: string;
  source?: string;
  company_id?: string;
  ticker?: string;
  document_id?: string;
  importance_score?: string;
  published_at?: string;
  payload?: Record<string, unknown>;
};

type TimeSeriesPoint = {
  date?: string;
  ts?: number;
  value?: number;
};

type TimeSeriesChartSeries = {
  label: string;
  ticker?: string;
  unit?: string;
  points: TimeSeriesPoint[];
};

type TimeSeriesChartPayload = {
  type: "timeseries";
  chart_style?: string;
  title?: string;
  subtitle?: string;
  unit?: string;
  series: TimeSeriesChartSeries[];
};

const modeStorageKey = "demo-domain-mode";

function toolKindLabel(kind: ToolEvent["toolKind"]) {
  if (kind === "mcp_tool") return "Context Surface";
  if (kind === "cache") return "Semantic Cache";
  return "Internal";
}

function formatTotalElapsedMs(ms: number) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 10000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms / 1000)}s`;
}

function formatDomainEventTime(publishedAt?: string) {
  if (!publishedAt) return "just now";
  const time = new Date(publishedAt);
  if (Number.isNaN(time.getTime())) return publishedAt;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(time);
}

function formatEventCount(count: number) {
  return `${count} event${count === 1 ? "" : "s"}`;
}

function mergeToolEvents(events: ToolEvent[]): MergedToolEvent[] {
  const merged: MergedToolEvent[] = [];
  const mergedByRunId = new Map<string, MergedToolEvent>();
  for (const ev of events) {
    const existing = mergedByRunId.get(ev.runId)
      ?? merged.find((item) =>
        item.resultPayload === undefined
        && item.toolName === ev.toolName
        && item.toolKind === ev.toolKind,
      );
    if (existing) {
      if (ev.status === "call") {
        existing.callPayload = ev.payload;
      } else {
        existing.resultPayload = ev.payload;
        existing.durationMs = ev.durationMs ?? existing.durationMs;
      }
      existing.ts = existing.ts ?? ev.ts;
      mergedByRunId.set(ev.runId, existing);
      continue;
    }
    const nextItem: MergedToolEvent = {
      runId: ev.runId,
      toolName: ev.toolName, toolKind: ev.toolKind,
      callPayload: ev.status === "call" ? ev.payload : undefined,
      resultPayload: ev.status === "result" ? ev.payload : undefined,
      durationMs: ev.durationMs,
      ts: ev.ts,
    };
    merged.push(nextItem);
    mergedByRunId.set(ev.runId, nextItem);
  }
  return merged;
}

type TraceTimelineEntry =
  | { kind: "step"; index: number; ts: number; step: ThinkingStep }
  | { kind: "tool"; index: number; ts: number; tool: MergedToolEvent };

function buildTraceTimeline(steps: ThinkingStep[], tools: MergedToolEvent[]): TraceTimelineEntry[] {
  const stepEntries = steps.map((step, index) => ({
    kind: "step" as const,
    index,
    ts: step.ts ?? 0,
    step,
  }));
  const toolEntries = tools.map((tool, index) => ({
    kind: "tool" as const,
    index,
    ts: tool.ts ?? 0,
    tool,
  }));
  return [...stepEntries, ...toolEntries].sort((a, b) => {
    if (a.ts !== b.ts) return a.ts - b.ts;
    if (a.kind !== b.kind) return a.kind === "step" ? -1 : 1;
    return a.index - b.index;
  });
}

function BrandLogo({ src, className = "brand-logo" }: { src?: string; className?: string }) {
  if (!src) {
    return <div className={className} />;
  }
  return (
    <span className={className} aria-hidden="true">
      <img src={src} alt="" />
    </span>
  );
}

function toolStatusLabel(tool: MergedToolEvent) {
  return tool.resultPayload === undefined ? "Running" : "Done";
}

function thinkingStepStatusLabel(step: ThinkingStep) {
  return step.durationText ? "Done" : "Running";
}

function MarkdownMessage({ content, collapseTables = false }: { content: string; collapseTables?: boolean }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
        table: ({ node: _node, ...props }) => {
          if (!collapseTables) {
            return <table {...props} />;
          }
          return (
            <details className="raw-data-table">
              <summary className="raw-data-table-summary">Raw data</summary>
              <div className="raw-data-table-wrap">
                <table {...props} />
              </div>
            </details>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function extractWrappedContextJson(raw: string): string | null {
  const startMarker = "content='";
  const start = raw.indexOf(startMarker);
  if (start < 0) return null;

  const contentStart = start + startMarker.length;
  let value = "";

  for (let index = contentStart; index < raw.length; index += 1) {
    const char = raw[index];
    const previousChar = index > contentStart ? raw[index - 1] : "";

    if (char === "'" && previousChar !== "\\") {
      return value;
    }

    value += char;
  }

  return null;
}

function parseWrappedContextJson(raw: string): unknown | null {
  const wrapped = extractWrappedContextJson(raw);
  if (!wrapped) return null;

  try {
    return JSON.parse(wrapped.replaceAll("\\'", "'"));
  } catch {
    return null;
  }
}

function normalizeToolPayload(payload: unknown): unknown {
  if (typeof payload === "string") {
    return parseWrappedContextJson(payload) ?? payload;
  }

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return payload;
  }

  if ("result" in payload && typeof payload.result === "string") {
    return parseWrappedContextJson(payload.result) ?? payload;
  }

  if ("raw_text" in payload && typeof payload.raw_text === "string") {
    return parseWrappedContextJson(payload.raw_text) ?? payload;
  }

  return payload;
}

function JsonToken({ value, className }: { value: string; className?: string }) {
  return <span className={className}>{value}</span>;
}

function renderJsonValue(value: unknown, depth = 0): React.JSX.Element {
  if (value === null) {
    return <JsonToken value="null" className="json-null" />;
  }

  if (typeof value === "string") {
    return <JsonToken value={JSON.stringify(value)} className="json-string" />;
  }

  if (typeof value === "number") {
    return <JsonToken value={String(value)} className="json-number" />;
  }

  if (typeof value === "boolean") {
    return <JsonToken value={String(value)} className="json-boolean" />;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <>
          <JsonToken value="[" className="json-punct" />
          <JsonToken value="]" className="json-punct" />
        </>
      );
    }

    return (
      <>
        <JsonToken value="[" className="json-punct" />
        {value.map((item, index) => (
          <div key={`array-${depth}-${index}`} className="json-line" style={{ paddingLeft: `${(depth + 1) * 1.25}rem` }}>
            {renderJsonValue(item, depth + 1)}
            {index < value.length - 1 && <JsonToken value="," className="json-punct" />}
          </div>
        ))}
        <div className="json-line" style={{ paddingLeft: `${depth * 1.25}rem` }}>
          <JsonToken value="]" className="json-punct" />
        </div>
      </>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value);

    if (entries.length === 0) {
      return (
        <>
          <JsonToken value="{" className="json-punct" />
          <JsonToken value="}" className="json-punct" />
        </>
      );
    }

    return (
      <>
        <JsonToken value="{" className="json-punct" />
        {entries.map(([key, entryValue], index) => (
          <div key={`object-${depth}-${key}`} className="json-line" style={{ paddingLeft: `${(depth + 1) * 1.25}rem` }}>
            <JsonToken value={JSON.stringify(key)} className="json-key" />
            <JsonToken value=": " className="json-punct" />
            {renderJsonValue(entryValue, depth + 1)}
            {index < entries.length - 1 && <JsonToken value="," className="json-punct" />}
          </div>
        ))}
        <div className="json-line" style={{ paddingLeft: `${depth * 1.25}rem` }}>
          <JsonToken value="}" className="json-punct" />
        </div>
      </>
    );
  }

  return <JsonToken value={JSON.stringify(String(value))} className="json-string" />;
}

function ToolPayloadJson({ payload }: { payload: unknown }) {
  const normalized = normalizeToolPayload(payload);

  return (
    <div className="json-scrollbox">
      <div className="json-tree">
        {renderJsonValue(normalized)}
      </div>
    </div>
  );
}

function compactNumber(value: number) {
  return new Intl.NumberFormat(undefined, {
    notation: Math.abs(value) >= 1000 ? "compact" : "standard",
    maximumFractionDigits: Math.abs(value) >= 1000 ? 1 : 2,
  }).format(value);
}

function readTimeSeriesChart(payload: unknown): { chart: TimeSeriesChartPayload; commands: string[] } | null {
  const normalized = normalizeToolPayload(payload);
  if (!normalized || typeof normalized !== "object" || Array.isArray(normalized)) return null;

  const chartCandidate = (normalized as Record<string, unknown>).chart;
  if (!chartCandidate || typeof chartCandidate !== "object" || Array.isArray(chartCandidate)) return null;

  const maybeChart = chartCandidate as Record<string, unknown>;
  const series = maybeChart.series;
  if (maybeChart.type !== "timeseries" || !Array.isArray(series)) return null;

  const commandsRaw = (normalized as Record<string, unknown>).redis_commands;
  const commands = Array.isArray(commandsRaw)
    ? commandsRaw.filter((value): value is string => typeof value === "string")
    : [];

  return {
    chart: maybeChart as unknown as TimeSeriesChartPayload,
    commands,
  };
}

function findTimeSeriesPayload(tools: MergedToolEvent[]): unknown | null {
  for (let index = tools.length - 1; index >= 0; index -= 1) {
    const payload = tools[index].resultPayload;
    if (payload && readTimeSeriesChart(payload)) {
      return payload;
    }
  }
  return null;
}

function TimeSeriesChartCard({ payload }: { payload: unknown }) {
  const parsed = readTimeSeriesChart(payload);
  if (!parsed) return null;

  const { chart, commands } = parsed;
  const [hoveredPoint, setHoveredPoint] = useState<{
    x: number;
    y: number;
    seriesLabel: string;
    dateLabel: string;
    value: number;
    color: string;
  } | null>(null);
  const palette = ["#6fd3ff", "#7bf0c8", "#ff9d6c", "#f8d26a", "#d8a6ff", "#9db6ff"];
  const width = 520;
  const height = 220;
  const padding = { left: 54, right: 18, top: 16, bottom: 34 };

  const normalizedSeries = chart.series
    .map((series, index) => {
      const points = (series.points || [])
        .map((point) => {
          const ts = typeof point.ts === "number"
            ? point.ts
            : typeof point.date === "string"
              ? new Date(point.date).getTime()
              : Number.NaN;
          const value = typeof point.value === "number" ? point.value : Number.NaN;
          const dateLabel = point.date ?? (Number.isFinite(ts) ? new Date(ts).toISOString().slice(0, 10) : "");
          return { ts, value, dateLabel };
        })
        .filter((point) => Number.isFinite(point.ts) && Number.isFinite(point.value))
        .sort((a, b) => a.ts - b.ts);
      return {
        ...series,
        color: palette[index % palette.length],
        points,
      };
    })
    .filter((series) => series.points.length > 0);

  if (normalizedSeries.length === 0) return null;

  const allPoints = normalizedSeries.flatMap((series) => series.points);
  let minX = Math.min(...allPoints.map((point) => point.ts));
  let maxX = Math.max(...allPoints.map((point) => point.ts));
  let minY = Math.min(...allPoints.map((point) => point.value));
  let maxY = Math.max(...allPoints.map((point) => point.value));

  if (minX === maxX) {
    minX -= 1;
    maxX += 1;
  }
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }

  const xScale = (ts: number) =>
    padding.left + ((ts - minX) / (maxX - minX)) * (width - padding.left - padding.right);
  const yScale = (value: number) =>
    height - padding.bottom - ((value - minY) / (maxY - minY)) * (height - padding.top - padding.bottom);

  const startLabel = new Date(minX).toISOString().slice(0, 10);
  const endLabel = new Date(maxX).toISOString().slice(0, 10);
  const yTicks = [maxY, minY + (maxY - minY) / 2, minY];

  function updateHoveredPoint(clientX: number, element: SVGSVGElement) {
    const rect = element.getBoundingClientRect();
    const svgX = ((clientX - rect.left) / rect.width) * width;
    let nearest:
      | {
          x: number;
          y: number;
          seriesLabel: string;
          dateLabel: string;
          value: number;
          color: string;
          distance: number;
        }
      | null = null;

    for (const series of normalizedSeries) {
      for (const point of series.points) {
        const x = xScale(point.ts);
        const distance = Math.abs(x - svgX);
        if (!nearest || distance < nearest.distance) {
          nearest = {
            x,
            y: yScale(point.value),
            seriesLabel: series.label,
            dateLabel: point.dateLabel,
            value: point.value,
            color: series.color,
            distance,
          };
        }
      }
    }

    if (!nearest) {
      setHoveredPoint(null);
      return;
    }

    setHoveredPoint({
      x: nearest.x,
      y: nearest.y,
      seriesLabel: nearest.seriesLabel,
      dateLabel: nearest.dateLabel,
      value: nearest.value,
      color: nearest.color,
    });
  }

  return (
    <div className="timeseries-card">
      <div className="timeseries-card-head">
        <div>
          <div className="timeseries-title">{chart.title ?? "RedisTimeSeries result"}</div>
          {chart.subtitle && <div className="timeseries-subtitle">{chart.subtitle}</div>}
        </div>
        {chart.unit && <div className="timeseries-unit">{chart.unit}</div>}
      </div>
      {commands.length > 0 && (
        <div className="timeseries-command-block">
          <div className="tool-detail-label">RedisTimeSeries Command</div>
          <pre className="timeseries-command">{commands.join("\n")}</pre>
        </div>
      )}
      <div className="timeseries-chart-shell">
        {hoveredPoint && (
          <div
            className="timeseries-tooltip"
            style={{
              left: `${Math.min(84, Math.max(16, (hoveredPoint.x / width) * 100))}%`,
              top: `${Math.min(74, Math.max(14, (hoveredPoint.y / height) * 100))}%`,
            }}
          >
            <div className="timeseries-tooltip-title">{hoveredPoint.seriesLabel}</div>
            <div className="timeseries-tooltip-date">{hoveredPoint.dateLabel}</div>
            <div className="timeseries-tooltip-value" style={{ color: hoveredPoint.color }}>
              {compactNumber(hoveredPoint.value)}
            </div>
          </div>
        )}
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="timeseries-chart"
          role="img"
          aria-label={chart.title ?? "RedisTimeSeries chart"}
          onMouseLeave={() => setHoveredPoint(null)}
          onMouseMove={(event) => updateHoveredPoint(event.clientX, event.currentTarget)}
        >
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={padding.left}
                x2={width - padding.right}
                y1={yScale(tick)}
                y2={yScale(tick)}
                className="timeseries-grid"
              />
              <text x={padding.left - 8} y={yScale(tick) + 4} textAnchor="end" className="timeseries-axis-label">
                {compactNumber(tick)}
              </text>
            </g>
          ))}
          {hoveredPoint && (
            <line
              x1={hoveredPoint.x}
              x2={hoveredPoint.x}
              y1={padding.top}
              y2={height - padding.bottom}
              className="timeseries-crosshair"
            />
          )}
          {normalizedSeries.map((series) => {
            const linePoints = series.points.map((point) => `${xScale(point.ts)},${yScale(point.value)}`).join(" ");
            const lastPoint = series.points[series.points.length - 1];
            return (
              <g key={series.label}>
                <polyline
                  fill="none"
                  stroke={series.color}
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  points={linePoints}
                />
                {series.points.map((point) => {
                  const x = xScale(point.ts);
                  const y = yScale(point.value);
                  const isHovered =
                    hoveredPoint &&
                    hoveredPoint.seriesLabel === series.label &&
                    hoveredPoint.dateLabel === point.dateLabel &&
                    hoveredPoint.value === point.value;
                  return (
                    <circle
                      key={`${series.label}-${point.dateLabel}`}
                      cx={x}
                      cy={y}
                      r={isHovered ? "4.5" : "0"}
                      fill={series.color}
                    />
                  );
                })}
                <circle cx={xScale(lastPoint.ts)} cy={yScale(lastPoint.value)} r="3.5" fill={series.color} />
              </g>
            );
          })}
          <text x={padding.left} y={height - 8} className="timeseries-axis-label">{startLabel}</text>
          <text x={width - padding.right} y={height - 8} textAnchor="end" className="timeseries-axis-label">{endLabel}</text>
        </svg>
      </div>
      <div className="timeseries-legend">
        {normalizedSeries.map((series) => {
          const lastPoint = series.points[series.points.length - 1];
          return (
            <div key={series.label} className="timeseries-legend-item">
              <span className="timeseries-legend-swatch" style={{ backgroundColor: series.color }} />
              <span className="timeseries-legend-label">{series.label}</span>
              <span className="timeseries-legend-value">{compactNumber(lastPoint.value)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<HealthState>(null);
  const [domain, setDomain] = useState<DomainConfig>(null);
  const [mode, setMode] = useState<AgentMode>(() => (localStorage.getItem(modeStorageKey) as AgentMode) || "context_surfaces");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [liveEvents, setLiveEvents] = useState<DomainEvent[]>([]);
  const [liveFeedConnected, setLiveFeedConnected] = useState(false);
  const [liveFeedExpanded, setLiveFeedExpanded] = useState(false);
  const [liveFeedTicker, setLiveFeedTicker] = useState<{ streamId: string; headline: string; timestamp: string } | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamAnnouncement, setStreamAnnouncement] = useState("");
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [selectedDemoUserId, setSelectedDemoUserId] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const liveFeedHydratedRef = useRef(false);
  const liveFeedTickerTimeoutRef = useRef<number | null>(null);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    void fetch("/api/health")
      .then((r) => r.json())
      .then((p: HealthState) => setHealth(p))
      .catch(() => setHealth({ ok: false, domain: "unknown", mcp_enabled: false, internal_tools: [], mcp_tools: [] }));
  }, []);

  useEffect(() => {
    void fetch("/api/domain-config")
      .then((r) => r.json())
      .then((p: DomainConfig) => {
        setDomain(p);
        setSelectedDemoUserId(p?.default_demo_user_id ?? p?.demo_users?.[0]?.id ?? "");
      })
      .catch(() => setDomain(null));
  }, []);

  useEffect(() => { localStorage.setItem(modeStorageKey, mode); }, [mode]);

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, isLoading]);

  useEffect(() => {
    if (!domain) return;
    Object.entries(domain.theme).forEach(([key, value]) => {
      document.documentElement.style.setProperty(`--${key.replaceAll("_", "-")}`, value);
    });
    document.documentElement.style.colorScheme = isLightColor(domain.theme.bg) ? "light" : "dark";
  }, [domain]);

  useEffect(() => {
    if (!domain?.ui?.show_live_updates) {
      setLiveEvents([]);
      setLiveFeedConnected(false);
      setLiveFeedTicker(null);
      return undefined;
    }

    setLiveEvents([]);
    setLiveFeedTicker(null);
    liveFeedHydratedRef.current = false;
    const hydrationTimer = window.setTimeout(() => {
      liveFeedHydratedRef.current = true;
    }, 1200);
    const source = new EventSource("/api/domain-events/stream?cursor=$");

    source.onopen = () => setLiveFeedConnected(true);
    source.onerror = () => setLiveFeedConnected(false);
    source.addEventListener("domain-event", (event) => {
      const messageEvent = event as MessageEvent<string>;
      try {
        const nextEvent = JSON.parse(messageEvent.data) as DomainEvent;
        setLiveEvents((current) => {
          if (current.some((entry) => entry.stream_id === nextEvent.stream_id)) return current;
          if (liveFeedHydratedRef.current && !liveFeedExpanded) {
            setLiveFeedTicker({
              streamId: nextEvent.stream_id,
              headline: nextEvent.headline,
              timestamp: formatDomainEventTime(nextEvent.published_at),
            });
            if (liveFeedTickerTimeoutRef.current !== null) {
              window.clearTimeout(liveFeedTickerTimeoutRef.current);
            }
            liveFeedTickerTimeoutRef.current = window.setTimeout(() => {
              setLiveFeedTicker(null);
              liveFeedTickerTimeoutRef.current = null;
            }, 18000);
          }
          return [nextEvent, ...current].slice(0, 6);
        });
      } catch {
        // Ignore malformed stream payloads so one bad event does not break the feed.
      }
    });

    return () => {
      window.clearTimeout(hydrationTimer);
      if (liveFeedTickerTimeoutRef.current !== null) {
        window.clearTimeout(liveFeedTickerTimeoutRef.current);
        liveFeedTickerTimeoutRef.current = null;
      }
      source.close();
    };
  }, [domain, liveFeedExpanded]);

  useEffect(() => {
    if (liveFeedExpanded) {
      setLiveFeedTicker(null);
      if (liveFeedTickerTimeoutRef.current !== null) {
        window.clearTimeout(liveFeedTickerTimeoutRef.current);
        liveFeedTickerTimeoutRef.current = null;
      }
    }
  }, [liveFeedExpanded]);

  useEffect(() => {
    document.title = domain?.app_name ?? "Domain Demo";
  }, [domain]);

  function resetConversation() {
    setMessages([]);
    setThreadId(crypto.randomUUID());
  }

  async function submitPrompt(prompt: string, event?: FormEvent) {
    event?.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || isLoading) return;

    const emptyMsg = (): ChatMessage => ({ id: "", role: "assistant", content: "", statusMessages: [], thinkingSteps: [], toolEvents: [] });
    const userMsg: ChatMessage = { ...emptyMsg(), id: `user-${Date.now()}`, role: "user" , content: trimmed };
    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = { ...emptyMsg(), id: assistantId };
    const nextMessages = [...messages, userMsg];
    setMessages([...nextMessages, assistantMsg]);
    setInput("");
    setIsLoading(true);
    setStreamAnnouncement("Response in progress.");

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map(({ role, content }) => ({ role, content })),
          mode,
          thread_id: threadId,
          demo_user_id: selectedDemoUserId || null,
        }),
      });

      if (!response.ok) {
        let errorMessage = `Request failed with status ${response.status}`;
        try {
          const payload = await response.json();
          if (payload && typeof payload.detail === "string") errorMessage = payload.detail;
        } catch {
          // Keep the HTTP status fallback if the server does not return JSON.
        }
        setMessages((cur) =>
          cur.map((m) => m.id === assistantId ? { ...m, content: errorMessage } : m),
        );
        setIsLoading(false);
        setStreamAnnouncement(`Request failed: ${errorMessage}`);
        return;
      }

      if (!response.body) { setIsLoading(false); return; }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const ev = JSON.parse(part.slice(6));
          setMessages((cur) =>
            cur.map((m) => {
              if (m.id !== assistantId) return m;
              switch (ev.type) {
                case "status":
                  return { ...m, statusMessages: [...m.statusMessages, { text: ev.text, ts: ev.ts ?? 0 }] };
                case "thinking-step":
                  return {
                    ...m,
                    thinkingSteps: [...m.thinkingSteps, {
                      id: ev.stepId ?? `step-${m.thinkingSteps.length}-${ev.ts ?? 0}`,
                      text: ev.step,
                      ts: ev.ts ?? 0,
                      kind: ev.stepKind === "llm" ? "llm" : "plan",
                    }],
                  };
                case "thinking-step-finish":
                  return {
                    ...m,
                    thinkingSteps: m.thinkingSteps.map((step) =>
                      step.id === ev.stepId
                        ? {
                            ...step,
                            durationMs: ev.durationMs,
                            durationText: ev.durationText,
                          }
                        : step,
                    ),
                  };
                case "tool-call":
                case "tool-result":
                  return { ...m, toolEvents: [...m.toolEvents, {
                    runId: ev.runId ?? `${ev.toolName}-${m.toolEvents.length}`,
                    toolName: ev.toolName, toolKind: ev.toolKind ?? "internal_function",
                    status: ev.type === "tool-call" ? "call" : "result",
                    payload: ev.payload ?? {}, durationMs: ev.durationMs, ts: ev.ts ?? 0,
                  }] };
                case "text-delta":
                  return { ...m, content: m.content + (ev.delta ?? "") };
                case "done":
                  return { ...m, totalElapsedMs: ev.totalElapsedMs };
                default:
                  return m;
              }
            }),
          );
        }
      }
      setStreamAnnouncement("Response complete.");
    } catch (err) {
      setMessages((cur) =>
        cur.map((m) => m.id === assistantId ? { ...m, content: m.content || "Connection error. Please try again." } : m),
      );
      setStreamAnnouncement("Connection error. Please try again.");
    }
    setIsLoading(false);
  }

  async function handleSubmit(event?: FormEvent) { await submitPrompt(input, event); }
  function handleQuickStart(prompt: string) {
    if (isLoading) return;
    setInput(prompt);
    void submitPrompt(prompt);
  }
  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    void handleSubmit();
  }

  return (
    <div className="shell">
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{streamAnnouncement}</div>
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <div className="brand">
              <BrandLogo src={domain?.logo_src} className="brand-logo" />
              <div className="brand-copy">
                <div className="brand-name">{domain?.app_name ?? "Demo"}</div>
                <div className="brand-subtitle">{domain?.subtitle ?? "Context Surfaces"}</div>
              </div>
            </div>
          </div>
          <div className="topbar-controls">
            {mode === "context_surfaces" && domain?.demo_users && domain.demo_users.length > 0 && (
              <label className="demo-user-picker">
                <span className="demo-user-label">Passenger</span>
                <span className="demo-user-select-shell">
                  <span className="demo-user-select-accent" aria-hidden="true" />
                  <select
                    value={selectedDemoUserId}
                    disabled={isLoading}
                    onChange={(event) => {
                      setSelectedDemoUserId(event.target.value);
                      resetConversation();
                    }}
                  >
                    {domain.demo_users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.subtitle ? `${user.label} • ${user.subtitle}` : user.label}
                      </option>
                    ))}
                  </select>
                  <span className="demo-user-select-arrow" aria-hidden="true">⌄</span>
                </span>
              </label>
            )}
            <div className="mode-toggle">
              <button disabled={isLoading} aria-pressed={mode === "context_surfaces"} className={`mode-btn ${mode === "context_surfaces" ? "active" : ""}`} onClick={() => { setMode("context_surfaces"); resetConversation(); }} type="button">Context Surfaces</button>
              <button disabled={isLoading} aria-pressed={mode === "simple_rag"} className={`mode-btn ${mode === "simple_rag" ? "active" : ""}`} onClick={() => { setMode("simple_rag"); resetConversation(); }} type="button">Simple RAG</button>
            </div>
          </div>
        </header>

        <section className={`workspace ${hasMessages ? "has-messages" : "is-empty"}`}>
          <div className={`conversation ${hasMessages ? "has-messages" : "is-empty"}`}>
            {!hasMessages && (
              <div className="hero-panel">
                <div className="hero-mark"><BrandLogo src={domain?.logo_src} className="hero-logo" /></div>
                <h1 className="hero-title">{domain?.hero_title ?? "How can we help?"}</h1>
                {domain?.subtitle && <div className="hero-tagline">{domain.subtitle}</div>}
              </div>
            )}

            {messages.map((message) => {
              const toolRows = mergeToolEvents(message.toolEvents);
              const chartPayload = findTimeSeriesPayload(toolRows);
              const traceTimeline = buildTraceTimeline(message.thinkingSteps, toolRows);
              const isAssistant = message.role === "assistant";
              const lastStatus = isAssistant && message.statusMessages.length > 0 ? message.statusMessages[message.statusMessages.length - 1] : null;
              const showStatus = isAssistant && !message.content && lastStatus;
              return (
                <article key={message.id} className={`message-block ${message.role}`}>
                  {showStatus && (
                    <div className="status-line">⏳ {lastStatus.text}</div>
                  )}
                  {isAssistant && (message.thinkingSteps.length > 0 || toolRows.length > 0) && (
                    <details className="trace-panel" open>
                      <summary className="trace-panel-summary">
                        <span className="trace-title">Agent Trace</span>
                        <span className="trace-counts">
                          {message.thinkingSteps.length > 0 && <span>{message.thinkingSteps.length} steps</span>}
                          {toolRows.length > 0 && <span>{toolRows.length} tool{toolRows.length > 1 ? "s" : ""}</span>}
                        </span>
                      </summary>
                      <div className="trace-panel-body">
                        {traceTimeline.map((entry) => (
                          entry.kind === "step" ? (
                            <div key={`${message.id}-step-${entry.step.id}`} className="trace-line">
                              <div className="trace-line-main">
                                <span className="trace-pill">{entry.step.kind}</span>
                                <span className="trace-line-text">{entry.step.text}</span>
                                {entry.step.kind === "llm" && (
                                  <span className={`tool-status ${entry.step.durationText ? "is-done" : "is-running"}`}>
                                    {!entry.step.durationText && <span className="tool-spinner" aria-hidden="true" />}
                                    {thinkingStepStatusLabel(entry.step)}
                                  </span>
                                )}
                              </div>
                              <div className="trace-line-right">
                                {entry.step.durationText ? (
                                  <span className="trace-latency">{entry.step.durationText}</span>
                                ) : entry.step.kind === "llm" ? (
                                  <span className="trace-latency trace-latency-pending">In flight</span>
                                ) : null}
                              </div>
                            </div>
                          ) : (
                          <details key={`${message.id}-tool-${entry.index}`} className="tool-item">
                            <summary className="tool-summary">
                              <div className="tool-header">
                                <span className={`tool-source ${entry.tool.toolKind}`}>{toolKindLabel(entry.tool.toolKind)}</span>
                                <span className="tool-name">{entry.tool.toolName}</span>
                                <span className={`tool-status ${entry.tool.resultPayload === undefined ? "is-running" : "is-done"}`}>
                                  {entry.tool.resultPayload === undefined && <span className="tool-spinner" aria-hidden="true" />}
                                  {toolStatusLabel(entry.tool)}
                                </span>
                              </div>
                              <div className="tool-summary-right">
                                {entry.tool.durationMs !== undefined ? (
                                  <span className="trace-latency">{entry.tool.durationMs}ms</span>
                                ) : (
                                  <span className="trace-latency trace-latency-pending">In flight</span>
                                )}
                              </div>
                            </summary>
                            <div className="tool-item-body">
                              {entry.tool.callPayload && (
                                <div className="tool-detail-section">
                                  <div className="tool-detail-label">Request</div>
                                  <ToolPayloadJson payload={entry.tool.callPayload} />
                                </div>
                              )}
                              {entry.tool.resultPayload ? (
                                <div className="tool-detail-section">
                                  <div className="tool-detail-label">Response</div>
                                  <ToolPayloadJson payload={entry.tool.resultPayload} />
                                </div>
                              ) : (
                                <div className="tool-detail-pending">
                                  <span className="tool-spinner" aria-hidden="true" />
                                  Waiting for tool response…
                                </div>
                              )}
                            </div>
                          </details>
                          )
                        ))}
                      </div>
                    </details>
                  )}
                  {message.content && (
                    <div className="message-bubble">
                      {message.role === "assistant" ? (
                        <MarkdownMessage content={message.content} collapseTables={!!chartPayload} />
                      ) : (
                        <div className="plain-text-message">{message.content}</div>
                      )}
                    </div>
                  )}
                  {isAssistant && !!chartPayload && (
                    <div className="message-artifact">
                      <TimeSeriesChartCard payload={chartPayload} />
                    </div>
                  )}
                  {isAssistant && message.totalElapsedMs !== undefined && (
                    <div className="message-meta">Completed in {formatTotalElapsedMs(message.totalElapsedMs)}</div>
                  )}
                </article>
              );
            })}
            <div ref={scrollRef} />
          </div>

          {health && domain?.ui?.show_platform_surface && (
            <section className="platform-panel" aria-label="Tool and Redis platform overview">
              <details className="platform-panel-details">
                <summary className="platform-panel-summary">
                  <div>
                    <div className="live-feed-eyebrow">{domain?.ui?.platform_surface_eyebrow ?? "Platform surface"}</div>
                    <div className="live-feed-title">{domain?.ui?.platform_surface_title ?? "Available tools and data planes"}</div>
                  </div>
                </summary>
                <div className="platform-grid">
                  <details className="platform-card">
                    <summary className="platform-card-summary">
                      <span className="platform-card-title">Internal tools</span>
                      <span className="platform-card-summary-right">
                        <span className="platform-card-count">{health.internal_tools.length}</span>
                      </span>
                    </summary>
                    <div className="platform-chip-cloud">
                      {health.internal_tools.map((toolName) => (
                        <span key={toolName} className="platform-chip internal">{toolName}</span>
                      ))}
                    </div>
                  </details>
                  <details className="platform-card">
                    <summary className="platform-card-summary">
                      <span className="platform-card-title">Context Surface tools</span>
                      <span className="platform-card-summary-right">
                        <span className="platform-card-count">{health.mcp_tools.length}</span>
                      </span>
                    </summary>
                    <div className="platform-chip-cloud">
                      {health.mcp_tools.map((toolName) => (
                        <span key={toolName} className="platform-chip mcp">{toolName}</span>
                      ))}
                    </div>
                  </details>
                  <details className="platform-card">
                    <summary className="platform-card-summary">
                      <span className="platform-card-title">Redis data planes</span>
                      <span className="platform-card-summary-right">
                        <span className="platform-card-count">{domain?.ui?.platform_data_planes?.length ?? 0}</span>
                      </span>
                    </summary>
                    <div className="platform-chip-cloud">
                      {(domain?.ui?.platform_data_planes ?? []).map((plane) => (
                        <span key={plane} className="platform-chip plane">{plane}</span>
                      ))}
                    </div>
                  </details>
                </div>
              </details>
            </section>
          )}

          {domain?.ui?.show_live_updates && (
            <aside className="live-feed-panel" aria-label="Live domain updates">
              <button
                className="live-feed-header live-feed-toggle"
                type="button"
                onClick={() => setLiveFeedExpanded((current) => !current)}
                aria-expanded={liveFeedExpanded}
              >
                <div className="live-feed-header-copy">
                  <div>
                    <div className="live-feed-eyebrow">{domain?.ui?.live_updates_eyebrow ?? "Live updates"}</div>
                    <div className="live-feed-title">{domain?.ui?.live_updates_title ?? "Live update feed"}</div>
                  </div>
                  {!liveFeedExpanded && liveFeedTicker ? (
                    <div key={liveFeedTicker.streamId} className="live-feed-marquee-shell">
                      <div className="live-feed-marquee">
                        <span>{liveFeedTicker.headline}</span>
                        <span className="live-feed-marquee-separator">•</span>
                        <span>{liveFeedTicker.timestamp}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="live-feed-collapsed-meta">
                      <span>{formatEventCount(liveEvents.length)}</span>
                      <span>{liveFeedConnected ? "Streaming" : "Idle"}</span>
                    </div>
                  )}
                </div>
                <div className="live-feed-header-right">
                  <div className={`live-feed-status ${liveFeedConnected ? "is-live" : "is-idle"}`}>
                    {liveFeedConnected ? "Streaming" : "Idle"}
                  </div>
                  <span className="live-feed-toggle-icon" aria-hidden="true">{liveFeedExpanded ? "−" : "+"}</span>
                </div>
              </button>
              {liveFeedExpanded && (
                <div className="live-feed-list">
                  {liveEvents.length > 0 ? liveEvents.map((event) => (
                    <article key={event.stream_id} className="live-feed-item">
                      <div className="live-feed-item-top">
                        <div className="live-feed-labels">
                          <span className="live-feed-pill">{event.event_family}</span>
                          <span className="live-feed-pill subtle">{event.event_type}</span>
                        </div>
                        <span className="live-feed-time">{formatDomainEventTime(event.published_at)}</span>
                      </div>
                      <div className="live-feed-headline">{event.headline}</div>
                      {event.message && <div className="live-feed-message">{event.message}</div>}
                      <div className="live-feed-meta">
                        {event.ticker && <span>{event.ticker}</span>}
                        {event.source && <span>{event.source}</span>}
                        {event.importance_score && <span>Importance {event.importance_score}</span>}
                      </div>
                    </article>
                  )) : (
                    <div className="live-feed-empty">
                      Waiting for the active domain to publish coverage updates into Redis.
                    </div>
                  )}
                </div>
              )}
            </aside>
          )}

          <form className={`composer ${hasMessages ? "thread" : "hero"}`} onSubmit={handleSubmit}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder={domain?.placeholder_text ?? "Ask a question..."}
              readOnly={isLoading}
              aria-busy={isLoading}
            />
            <div className="composer-footer">
              <div className="composer-hint">{isLoading ? "Response in progress" : "Press Enter to send"}</div>
              <button className="send-button" type="submit" disabled={isLoading}>Send</button>
            </div>
          </form>

          {!hasMessages && (
            <div className="quick-starts">
              <div className="quick-starts-label">Try asking</div>
              <div className="quick-starts-row">
                {(domain?.starter_prompts ?? []).map((p) => (
                  <button key={p.title} className="quick-start-chip" onClick={() => handleQuickStart(p.prompt)} type="button" disabled={isLoading}>{p.title}</button>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
