"use client";

import { useEffect, useRef, useState } from "react";
import PageShell from "@/components/PageShell";
import { api, type DocumentItem } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  pending: "в очереди",
  indexing: "индексация…",
  ready: "готов",
  failed: "ошибка",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [types, setTypes] = useState<{ slug: string; name: string }[]>([]);
  const [docType, setDocType] = useState("order");
  const [instructions, setInstructions] = useState("");
  const [format, setFormat] = useState<"docx" | "pdf">("docx");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.documents().then(setDocuments).catch(() => setDocuments([]));
    api.documentTypes().then(setTypes).catch(() => setTypes([]));
  }, []);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const doc = await api.uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
      if (fileRef.current) fileRef.current.value = "";
      setMessage(`«${doc.title}» загружен и проиндексирован (категория: ${doc.category}).`);
    } catch (e) {
      setMessage(
        String(e).includes("402")
          ? "Загрузка документов доступна с тарифа HR Pro."
          : `Не удалось загрузить: ${String(e)}`,
      );
    } finally {
      setBusy(false);
    }
  }

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api.generateDocument(docType, instructions, format);
      setMessage("Документ сформирован — файл скачивается.");
    } catch (e) {
      setMessage(`Не удалось сгенерировать: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell title="Документы" active="/documents">
      {message && <div className="notice">{message}</div>}

      <section className="panel">
        <h2>Генерация кадрового документа</h2>
        <p className="muted">
          AI составит документ по Трудовому кодексу РУз; недостающие данные будут отмечены
          плейсхолдерами.
        </p>
        <form onSubmit={generate} className="gen-form">
          <div className="row">
            <label>
              Тип документа
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {types.map((t) => (
                  <option key={t.slug} value={t.slug}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Формат
              <select value={format} onChange={(e) => setFormat(e.target.value as "docx" | "pdf")}>
                <option value="docx">DOCX</option>
                <option value="pdf">PDF</option>
              </select>
            </label>
          </div>
          <label>
            Данные для документа
            <textarea
              rows={4}
              required
              minLength={5}
              placeholder="Например: приказ о предоставлении ежегодного отпуска специалисту отдела кадров Каримовой Н. с 10 августа на 21 календарный день"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </label>
          <button className="primary" disabled={busy}>
            Сгенерировать и скачать
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>База знаний организации</h2>
        <div className="row">
          <input type="file" ref={fileRef} accept=".pdf,.docx,.xlsx,.txt,.md,.html" />
          <button onClick={upload} disabled={busy}>
            Загрузить
          </button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Категория</th>
              <th>Статус</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td>
                <td>{d.category}</td>
                <td>{STATUS_LABEL[d.status] ?? d.status}</td>
                <td>{new Date(d.created_at).toLocaleDateString("ru-RU")}</td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  Документы ещё не загружены.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </PageShell>
  );
}
