import { FormEvent, useEffect, useRef, useState } from "react";
import type {
  AgentMode,
  ChatMessage,
  DomainConfig,
  HealthState,
  MemoryDashboardState,
  RedisContextView,
  ToolDefinition,
} from "./types";
import { apiUrl, modeStorageKey } from "./utils";

import { EmptyState } from "./components/EmptyState";
import { ConversationView } from "./components/ConversationView";
import { ActivityPanel } from "./components/ActivityPanel";

function emptyMsg(): ChatMessage {
  return {
    id: "",
    role: "assistant",
    content: "",
    statusMessages: [],
    thinkingSteps: [],
    toolEvents: [],
  };
}

export default function App() {
  const [health, setHealth] = useState<HealthState>(null);
  const [domain, setDomain] = useState<DomainConfig>(null);
  const [mode, setMode] = useState<AgentMode>(
    () => (localStorage.getItem(modeStorageKey) as AgentMode) || "context_surfaces"
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());

  const [activityPanelOpen, setActivityPanelOpen] = useState(false);
  const [contextView, setContextView] = useState<RedisContextView>("activity");

  const [memoryLoading, setMemoryLoading] = useState(true);
  const [memoryData, setMemoryData] = useState<MemoryDashboardState>(null);
  const [toolsData, setToolsData] = useState<ToolDefinition[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const autoOpenedRef = useRef(false);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    let cancelled = false;
    const fetchHealth = () => {
      void fetch(apiUrl("/api/health"))
        .then((r) => r.json())
        .then((p: HealthState) => { if (!cancelled) setHealth(p); })
        .catch(() => {
          if (!cancelled) setTimeout(fetchHealth, 2000);
        });
    };
    fetchHealth();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchDomainConfig = () => {
      void fetch(apiUrl("/api/domain-config"))
        .then((r) => r.json())
        .then((p: DomainConfig) => {
          if (!cancelled) {
            setDomain(p);
            void loadMemoryDashboard();
            void loadTools();
          }
        })
        .catch(() => {
          if (!cancelled) setTimeout(fetchDomainConfig, 2000);
        });
    };
    fetchDomainConfig();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    localStorage.setItem(modeStorageKey, mode);
  }, [mode]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    document.title = domain?.app_name ?? "Redis Iris Demo";
  }, [domain]);

  useEffect(() => {
    if (!domain) return;
    const root = document.documentElement;
    if (domain.theme?.landing_bg) {
      root.style.setProperty("--landing-bg", domain.theme.landing_bg);
    }
    root.style.setProperty("--landing-left-img", `url('/backgrounds/${domain.id}/left.svg')`);
    root.style.setProperty("--landing-right-img", `url('/backgrounds/${domain.id}/right.svg')`);
    return () => {
      root.style.removeProperty("--landing-bg");
      root.style.removeProperty("--landing-left-img");
      root.style.removeProperty("--landing-right-img");
    };
  }, [domain]);

  useEffect(() => {
    if (autoOpenedRef.current || !hasMessages) return;
    let latest: ChatMessage | undefined;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") { latest = messages[i]; break; }
    }
    if (latest && latest.toolEvents.length > 0) {
      setActivityPanelOpen(true);
      setContextView("activity");
      autoOpenedRef.current = true;
    }
  }, [messages]);

  async function loadMemoryDashboard() {
    setMemoryLoading(true);
    try {
      const response = await fetch(
        `${apiUrl("/api/memory/dashboard")}?thread_id=${encodeURIComponent(threadId)}`
      );
      setMemoryData(await response.json());
    } catch {
      setMemoryData({
        enabled: false,
        short_term: [],
        long_term: [],
        errors: ["Unable to load memory dashboard."],
      });
    }
    setMemoryLoading(false);
  }

  async function loadTools() {
    setToolsLoading(true);
    try {
      const response = await fetch(apiUrl("/api/tools"));
      const data = await response.json();
      setToolsData(data.tools ?? []);
    } catch {
      setToolsData([]);
    }
    setToolsLoading(false);
  }

  function loadContext() {
    void loadMemoryDashboard();
    void loadTools();
  }

  function handleToggleRedisContext() {
    if (activityPanelOpen && contextView === "redis-context") {
      setActivityPanelOpen(false);
      return;
    }
    setContextView("redis-context");
    setActivityPanelOpen(true);
    loadContext();
  }

  function handleShowActivity() {
    setContextView("activity");
    setActivityPanelOpen(true);
  }

  function handleModeChange(newMode: AgentMode) {
    setMode(newMode);
    setMessages([]);
    setThreadId(crypto.randomUUID());
    setActivityPanelOpen(false);
    autoOpenedRef.current = false;
  }

  async function submitPrompt(prompt: string, event?: FormEvent) {
    event?.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || isLoading) return;

    const userMsg: ChatMessage = {
      ...emptyMsg(),
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = { ...emptyMsg(), id: assistantId };
    const nextMessages = [...messages, userMsg];
    setMessages([...nextMessages, assistantMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(apiUrl("/api/chat/stream"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map(({ role, content }) => ({ role, content })),
          mode,
          thread_id: threadId,
        }),
      });

      if (!response.body) {
        setIsLoading(false);
        return;
      }
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
                  return {
                    ...m,
                    statusMessages: [
                      ...m.statusMessages,
                      { text: ev.text, ts: ev.ts ?? 0 },
                    ],
                  };
                case "thinking-step":
                  return {
                    ...m,
                    thinkingSteps: [
                      ...m.thinkingSteps,
                      {
                        id:
                          ev.stepId ??
                          `step-${m.thinkingSteps.length}-${ev.ts ?? 0}`,
                        text: ev.step,
                        ts: ev.ts ?? 0,
                        kind: ev.stepKind === "llm" ? "llm" : "plan",
                      },
                    ],
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
                        : step
                    ),
                  };
                case "tool-call":
                case "tool-result":
                  return {
                    ...m,
                    toolEvents: [
                      ...m.toolEvents,
                      {
                        toolName: ev.toolName,
                        toolKind: ev.toolKind ?? "internal_function",
                        status: ev.type === "tool-call" ? "call" : "result",
                        payload: ev.payload ?? {},
                        durationMs: ev.durationMs,
                        ts: ev.ts ?? 0,
                      },
                    ],
                  };
                case "error":
                  if (import.meta.env.DEV) {
                    console.error(`[OpenAI Error] ${ev.errorType}: ${ev.message}`);
                  }
                  return m;
                case "text-delta":
                  return { ...m, content: m.content + (ev.delta ?? "") };
                default:
                  return m;
              }
            })
          );
        }
      }
    } catch (err) {
      setMessages((cur) =>
        cur.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content || "Connection error. Please try again." }
            : m
        )
      );
    }
    setIsLoading(false);
  }

  function handleSubmit(event?: FormEvent) {
    void submitPrompt(input, event);
  }

  function handlePrefill(prompt: string) {
    setInput(prompt);
  }

  const backendReady = domain !== null && !memoryLoading && !toolsLoading;
  const allQuickStarts = domain?.starter_prompts ?? [];

  function handleGoHome() {
    setMessages([]);
    setInput("");
    setThreadId(crypto.randomUUID());
    setActivityPanelOpen(false);
    autoOpenedRef.current = false;
  }

  if (!domain) {
    return (
      <div className="loading-overlay">
        <img src="/RedisTextLogo.png" alt="" />
        <span>Setting up demo…</span>
        <span>Please refresh if not auto-redirected in 30 seconds</span>
      </div>
    );
  }

  return (
    <div className={`shell ${activityPanelOpen ? "panel-open" : ""} ${!hasMessages ? "shell--landing" : ""}`}>
      <header className="topbar">
        <div className="topbar-brand" onClick={handleGoHome} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleGoHome(); }} role="button" tabIndex={0} style={{ cursor: "pointer" }}>
          {domain?.logo_src && <img src={domain.logo_src} alt="" className="topbar-brand-logo" />}
          <div className="brand-text">
            <span className="brand-name">{domain?.app_name ?? "Redis Iris"}</span>
            <span className="brand-subtitle">{domain?.subtitle ?? "AI Assistant"}</span>
          </div>
        </div>
        <div className="topbar-actions">
          <button
            className={`topbar-context-btn ${activityPanelOpen ? "active" : ""}`}
            onClick={handleToggleRedisContext}
            type="button"
          >
            <img src="/RedisLogo.png" alt="" className="topbar-context-logo" />
            <span>{mode === "simple_rag" ? "Redis Vector Search" : "Redis Iris"}</span>
          </button>
        </div>
      </header>

      <main className="main">
        {!hasMessages ? (
          <EmptyState
            domain={domain}
            backendReady={backendReady}
            input={input}
            onInputChange={setInput}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            mode={mode}
            onModeChange={handleModeChange}
            starterPrompts={allQuickStarts}
            onPrefill={handlePrefill}
          />
        ) : (
          <ConversationView
            messages={messages}
            isLoading={isLoading}
            scrollRef={scrollRef}
            input={input}
            onInputChange={setInput}
            onSubmit={handleSubmit}
            placeholder={
              domain?.placeholder_text ?? "Follow up..."
            }
            onShowActivity={handleShowActivity}
          />
        )}
      </main>

      <ActivityPanel
        allMessages={messages}
        isOpen={activityPanelOpen}
        onClose={() => setActivityPanelOpen(false)}
        contextView={contextView}
        onContextViewChange={setContextView}
        memoryData={memoryData}
        memoryLoading={memoryLoading}
        onRefreshMemory={loadMemoryDashboard}
        onLoadContext={loadContext}
        toolsData={toolsData}
        toolsLoading={toolsLoading}
        mode={mode}
        domain={domain}
      />
    </div>
  );
}
