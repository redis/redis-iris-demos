export type ChatRole = "user" | "assistant";

export type ToolEvent = {
  toolName: string;
  toolKind: "internal_function" | "mcp_tool" | "memory" | "langcache" | "guardrail";
  status: "call" | "result";
  payload: Record<string, unknown>;
  durationMs?: number;
  ts?: number;
};

export type MergedToolEvent = {
  toolName: string;
  toolKind: ToolEvent["toolKind"];
  callPayload?: Record<string, unknown>;
  resultPayload?: Record<string, unknown>;
  durationMs?: number;
  ts?: number;
};

export type ThinkingStep = {
  id: string;
  text: string;
  ts: number;
  kind: "plan" | "llm";
  durationMs?: number;
  durationText?: string;
};

export type StatusMessage = { text: string; ts: number };

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  statusMessages: StatusMessage[];
  thinkingSteps: ThinkingStep[];
  toolEvents: ToolEvent[];
};

export type HealthState = {
  ok: boolean;
  domain: string;
  mcp_enabled: boolean;
  memory_enabled?: boolean;
  langcache_enabled?: boolean;
  internal_tools: string[];
} | null;

export type MemoryDashboardState = {
  enabled: boolean;
  thread_id?: string | null;
  owner_id?: string;
  short_term: Array<Record<string, unknown>>;
  long_term: Array<Record<string, unknown>>;
  errors?: string[];
} | null;

export type AgentMode = "context_surfaces" | "simple_rag";

export type PromptCard = { eyebrow: string; title: string; prompt: string };

export type DemoUser = {
  id: string;
  label: string;
  subtitle?: string;
  cache_group_id?: string;
};

export type UiConfig = {
  show_platform_surface?: boolean;
  show_live_updates?: boolean;
  platform_surface_eyebrow?: string;
  platform_surface_title?: string;
  platform_data_planes?: string[];
  live_updates_eyebrow?: string;
  live_updates_title?: string;
};

export type DomainConfig = {
  id: string;
  app_name: string;
  subtitle: string;
  hero_title: string;
  placeholder_text: string;
  demo_steps: string[];
  starter_prompts: PromptCard[];
  theme: Record<string, string>;
  logo_src: string;
  ui?: UiConfig;
  demo_users?: DemoUser[];
  seed_langcache?: { prompt: string; response: string }[];
} | null;

export type ToolDefinition = {
  name: string;
  description: string;
  kind: "internal" | "mcp_tool";
  input_schema?: Record<string, unknown>;
};

export type ToolsResponse = {
  tools: ToolDefinition[];
  count: number;
};

export type RedisContextView = "activity" | "redis-context";
