"use client";

import { useEffect, useState } from "react";
import PageShell from "@/components/PageShell";
import {
  api,
  type ActItem,
  type ComplianceCheckItem,
  type DocumentItem,
  type NotificationItem,
} from "@/lib/api";

const SEVERITY_LABEL: Record<string, string> = {
  critical: "критично",
  warning: "внимание",
  info: "справочно",
};

export default function CompliancePage() {
  const [available, setAvailable] = useState(true);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [acts, setActs] = useState<ActItem[]>([]);
  const [watched, setWatched] = useState<Set<string>>(new Set());
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [checks, setChecks] = useState<ComplianceCheckItem[]>([]);
  const [busyDoc, setBusyDoc] = useState("");

  useEffect(() => {
    api
      .watches()
      .then((w) => setWatched(new Set(w.map((x) => x.act_id))))
      .catch((e) => {
        if (String(e).includes("402")) setAvailable(false);
      });
    api.notifications().then(setNotifications).catch(() => setNotifications([]));
    api.acts().then(setActs).catch(() => setActs([]));
    api.documents().then(setDocuments).catch(() => setDocuments([]));
    api.complianceChecks().then(setChecks).catch(() => setChecks([]));
  }, []);

  async function toggleWatch(actId: string) {
    const next = new Set(watched);
    if (next.has(actId)) {
      next.delete(actId);
      await api.unwatchAct(actId).catch(() => next.add(actId));
    } else {
      next.add(actId);
      await api.watchAct(actId).catch(() => next.delete(actId));
    }
    setWatched(new Set(next));
  }

  async function runCheck(documentId: string) {
    setBusyDoc(documentId);
    try {
      const check = await api.runComplianceCheck(documentId);
      setChecks((prev) => [check, ...prev]);
    } finally {
      setBusyDoc("");
    }
  }

  async function markAllRead() {
    await api.markNotificationsRead().catch(() => undefined);
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }

  if (!available) {
    return (
      <PageShell title="Compliance Center" active="/compliance">
        <div className="notice">
          Compliance Center доступен на тарифах <b>Enterprise</b> и <b>Government Edition</b>.
          Уведомления об изменениях законодательства и AI-проверка документов на соответствие —
          свяжитесь с нами для перехода на Enterprise.
        </div>
      </PageShell>
    );
  }

  const docTitle = (id: string) => documents.find((d) => d.id === id)?.title ?? id.slice(0, 8);

  return (
    <PageShell title="Compliance Center" active="/compliance">
      <section className="panel">
        <div className="row space-between">
          <h2>Уведомления</h2>
          {notifications.some((n) => !n.is_read) && (
            <button className="link-btn" onClick={markAllRead}>
              Отметить все прочитанными
            </button>
          )}
        </div>
        {notifications.length === 0 && <p className="muted">Изменений законодательства не обнаружено.</p>}
        {notifications.map((n) => (
          <div key={n.id} className={`notification ${n.is_read ? "" : "unread"}`}>
            <b>{n.title}</b>
            <p>{n.body}</p>
            {typeof n.meta.url === "string" && (
              <a href={n.meta.url} target="_blank" rel="noreferrer">
                Открыть акт ↗
              </a>
            )}
          </div>
        ))}
      </section>

      <section className="panel">
        <h2>Отслеживаемые акты</h2>
        <p className="muted">
          При выходе новой редакции отмеченных актов организация получит уведомление.
        </p>
        <table className="table">
          <tbody>
            {acts.map((a) => (
              <tr key={a.id}>
                <td>
                  <a href={a.url} target="_blank" rel="noreferrer">
                    {a.title}
                  </a>{" "}
                  <span className="muted">ред. {a.current_revision}</span>
                </td>
                <td style={{ width: 140 }}>
                  <button onClick={() => toggleWatch(a.id)}>
                    {watched.has(a.id) ? "★ Отслеживается" : "☆ Отслеживать"}
                  </button>
                </td>
              </tr>
            ))}
            {acts.length === 0 && (
              <tr>
                <td className="muted">Акты ещё не добавлены в мониторинг.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Проверка документов на соответствие</h2>
        <table className="table">
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td>
                <td style={{ width: 160 }}>
                  <button onClick={() => runCheck(d.id)} disabled={busyDoc === d.id}>
                    {busyDoc === d.id ? "Проверяем…" : "Проверить"}
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td className="muted">Загрузите документы на странице «Документы».</td>
              </tr>
            )}
          </tbody>
        </table>

        {checks.length > 0 && <h3>История проверок</h3>}
        {checks.map((c) => (
          <div key={c.check_id} className="check-card">
            <div className="row space-between">
              <b>{docTitle(c.document_id)}</b>
              <span className={`badge ${c.status}`}>
                {c.status === "ok" ? "соответствует" : c.status === "issues" ? "есть замечания" : "ошибка"}
              </span>
            </div>
            {c.findings.map((f, i) => (
              <div key={i} className={`finding ${f.severity}`}>
                <b>[{SEVERITY_LABEL[f.severity] ?? f.severity}]</b> {f.issue}
                {f.recommendation && <div className="muted">Рекомендация: {f.recommendation}</div>}
                {f.article && <div className="muted">Норма: {f.article}</div>}
              </div>
            ))}
          </div>
        ))}
      </section>
    </PageShell>
  );
}
