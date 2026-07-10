// Thin client for the LegalOS API (same-origin via Next.js rewrite → backend).

export interface Source {
  chunk_id: string;
  score: number;
  excerpt: string;
  title?: string;
  url?: string;
}

export interface ChatResponse {
  conversation_id: string;
  content: string;
  sources: Source[];
  blocked: boolean;
}

export interface Agent {
  slug: string;
  name: string;
  description: string;
  min_tier: string;
  available: boolean;
}

export interface Conversation {
  id: string;
  agent: string;
  title: string;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  category: string;
  status: string;
  mime_type: string;
  created_at: string;
}

export interface Plan {
  tier: string;
  messages_per_day: number;
  documents_per_day: number;
  document_upload: boolean;
  agents: string[];
}

export interface GovServiceItem {
  slug: string;
  title_ru: string;
  title_uz: string;
  url: string;
  agency: string;
}

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  meta: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface ComplianceFinding {
  severity: "critical" | "warning" | "info";
  issue: string;
  recommendation: string;
  article: string;
}

export interface ComplianceCheckItem {
  check_id: string;
  document_id: string;
  status: string;
  findings: ComplianceFinding[];
  created_at?: string;
}

export interface ActItem {
  id: string;
  source: string;
  title: string;
  url: string;
  act_type: string;
  current_revision: number;
}

const API = "/api/v1";

export const auth = {
  token: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem("legalos_token") : null,
  save(token: string) {
    localStorage.setItem("legalos_token", token);
  },
  logout() {
    localStorage.removeItem("legalos_token");
    window.location.href = "/login";
  },
};

function authHeaders(): Record<string, string> {
  const token = auth.token();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...init?.headers },
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  register: (email: string, password: string, organization = "") =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, organization }),
    }),
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API}/auth/login`, { method: "POST", body });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json() as Promise<{ access_token: string }>;
  },

  chat: (message: string, agent: string, conversationId?: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, agent, conversation_id: conversationId ?? null }),
    }),

  // SSE over fetch (EventSource can't POST). Calls onDelta per token,
  // resolves with the final frame.
  async chatStream(
    message: string,
    agent: string,
    conversationId: string | undefined,
    onDelta: (text: string) => void,
  ): Promise<{ conversation_id: string; sources: Source[]; blocked?: boolean }> {
    const res = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ message, agent, conversation_id: conversationId ?? null }),
    });
    if (res.status === 401 && typeof window !== "undefined") window.location.href = "/login";
    if (!res.ok || !res.body) throw new Error(`${res.status}: ${await res.text()}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let final: { conversation_id: string; sources: Source[]; blocked?: boolean } | null = null;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);
        if (!frame.startsWith("data: ")) continue;
        const payload = JSON.parse(frame.slice(6));
        if (payload.delta) onDelta(payload.delta);
        if (payload.done) final = payload;
        if (payload.error) throw new Error(payload.error);
      }
    }
    if (!final) throw new Error("stream ended without done frame");
    return final;
  },

  agents: () => request<Agent[]>("/agents"),
  conversations: () => request<Conversation[]>("/chat/conversations"),
  plan: () => request<Plan>("/billing/plan"),

  documents: () => request<DocumentItem[]>("/documents"),
  async uploadDocument(file: File): Promise<DocumentItem> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API}/documents`, { method: "POST", headers: authHeaders(), body: form });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  },
  documentTypes: () => request<{ slug: string; name: string }[]>("/documents/generate/types"),
  async generateDocument(docType: string, instructions: string, format: "docx" | "pdf"): Promise<void> {
    const res = await fetch(`${API}/documents/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ doc_type: docType, instructions, format }),
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") ?? "";
    const match = /filename\*=UTF-8''([^;]+)/.exec(disposition);
    const filename = match ? decodeURIComponent(match[1]) : `document.${format}`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  },

  govServices: (query?: string) =>
    request<GovServiceItem[]>(`/gov/services${query ? `?query=${encodeURIComponent(query)}` : ""}`),

  acts: () => request<ActItem[]>("/legislation/acts"),
  notifications: () => request<NotificationItem[]>("/compliance/notifications"),
  markNotificationsRead: () => request<void>("/compliance/notifications/read", { method: "POST" }),
  watches: () => request<{ act_id: string; title: string; url: string; since: string }[]>("/compliance/watches"),
  watchAct: (actId: string) => request<void>(`/compliance/watches/${actId}`, { method: "PUT" }),
  unwatchAct: (actId: string) => request<void>(`/compliance/watches/${actId}`, { method: "DELETE" }),
  complianceChecks: () => request<ComplianceCheckItem[]>("/compliance/checks"),
  runComplianceCheck: (documentId: string) =>
    request<ComplianceCheckItem>(`/compliance/checks/${documentId}`, { method: "POST" }),
};
