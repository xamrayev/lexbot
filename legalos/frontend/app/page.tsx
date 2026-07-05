"use client";

// Desktop workspace layout per product spec:
//   left  — navigation / agents / history
//   right — cited sources, law articles, government services deep links

import { useEffect, useRef, useState } from "react";
import {
  api,
  auth,
  type Agent,
  type Conversation,
  type GovServiceItem,
  type Plan,
  type Source,
} from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function Workspace() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activeAgent, setActiveAgent] = useState("hr");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [govServices, setGovServices] = useState<GovServiceItem[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!auth.token()) {
      window.location.href = "/login";
      return;
    }
    api.agents().then(setAgents).catch(() => setAgents([]));
    api.conversations().then(setConversations).catch(() => setConversations([]));
    api.plan().then(setPlan).catch(() => setPlan(null));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setBusy(true);

    api.govServices(text).then(setGovServices).catch(() => setGovServices([]));

    const appendDelta = (delta: string) =>
      setMessages((m) => {
        const next = [...m];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: next[next.length - 1].content + delta,
        };
        return next;
      });

    try {
      const final = await api.chatStream(text, activeAgent, conversationId, appendDelta);
      setConversationId(final.conversation_id);
      setSources(final.sources);
    } catch {
      // Streaming can be unavailable behind some proxies — fall back to the JSON endpoint.
      try {
        const res = await api.chat(text, activeAgent, conversationId);
        setConversationId(res.conversation_id);
        setSources(res.sources);
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = { role: "assistant", content: res.content, sources: res.sources };
          return next;
        });
      } catch (e) {
        appendDelta(`Ошибка: ${String(e)}`);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          Legal<span>OS</span>
        </div>
        <nav className="side-nav">
          <a href="/" className="active">
            Чат
          </a>
          <a href="/documents">Документы</a>
          <a href="/compliance">Комплаенс</a>
        </nav>
        {plan && (
          <div className="muted">
            Тариф: <span className="badge">{plan.tier}</span>
          </div>
        )}
        <div>
          <div className="section-title">Агенты</div>
          {agents.map((a) => (
            <button
              key={a.slug}
              className={`agent-item ${a.slug === activeAgent ? "active" : ""} ${a.available ? "" : "locked"}`}
              disabled={!a.available}
              title={a.available ? a.description : `Доступно с тарифа ${a.min_tier}`}
              onClick={() => {
                setActiveAgent(a.slug);
                setConversationId(undefined);
                setMessages([]);
                setSources([]);
              }}
            >
              {a.name} {a.available ? "" : "🔒"}
            </button>
          ))}
        </div>
        <div>
          <div className="section-title">История</div>
          {conversations.map((c) => (
            <button key={c.id} className="history-item" onClick={() => setConversationId(c.id)}>
              {c.title}
            </button>
          ))}
          {conversations.length === 0 && <div className="muted">Пока нет диалогов</div>}
        </div>
        <div style={{ marginTop: "auto" }}>
          <button className="link-btn" onClick={() => auth.logout()}>
            Выйти
          </button>
        </div>
      </aside>

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="muted">
              Задайте вопрос по законодательству Республики Узбекистан — например: «Как оформить
              ежегодный отпуск?» или «Как зарегистрировать ООО?»
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.content || (busy && i === messages.length - 1 ? "…" : "")}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="composer">
          <input
            value={input}
            placeholder="Ваш вопрос…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button onClick={send} disabled={busy}>
            Отправить
          </button>
        </div>
      </main>

      <aside className="source-panel">
        <div className="section-title">Источники</div>
        {sources.length === 0 && (
          <div className="muted">
            Здесь появятся статьи законов и фрагменты документов, использованные в ответе, со
            ссылками на Lex.uz и Norma.uz.
          </div>
        )}
        {sources.map((s, i) => (
          <div key={s.chunk_id} className="source-card">
            <div className="section-title">
              Источник {i + 1} {s.title ? `— ${s.title}` : ""}
            </div>
            <p>
              <mark>{s.excerpt}</mark>…
            </p>
            {s.url && (
              <a href={s.url} target="_blank" rel="noreferrer">
                Открыть первоисточник ↗
              </a>
            )}
          </div>
        ))}

        {govServices.length > 0 && (
          <>
            <div className="section-title" style={{ marginTop: 16 }}>
              Государственные сервисы
            </div>
            {govServices.map((g) => (
              <div key={g.slug} className="source-card">
                <b>{g.title_ru}</b>
                <div className="muted">{g.agency}</div>
                <a href={g.url} target="_blank" rel="noreferrer">
                  Перейти на портал ↗
                </a>
              </div>
            ))}
          </>
        )}
      </aside>
    </div>
  );
}
