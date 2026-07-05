"use client";

import { useState } from "react";
import { api, auth } from "@/lib/api";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organization, setOrganization] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password, organization);
      auth.save(result.access_token);
      window.location.href = "/";
    } catch {
      setError(
        mode === "login"
          ? "Неверный email или пароль."
          : "Не удалось зарегистрироваться. Проверьте данные (пароль — от 8 символов).",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <div className="brand" style={{ fontSize: 24, textAlign: "center" }}>
          Legal<span>OS</span>
        </div>
        <p className="muted" style={{ textAlign: "center" }}>
          AI-платформа для юристов, кадров и бухгалтерии — Республика Узбекистан
        </p>

        <div className="tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            Вход
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Регистрация
          </button>
        </div>

        <label>
          Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Пароль
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {mode === "register" && (
          <label>
            Организация <span className="muted">(пусто — личный кабинет HR, тариф Free)</span>
            <input value={organization} onChange={(e) => setOrganization(e.target.value)} />
          </label>
        )}

        {error && <div className="error">{error}</div>}

        <button className="primary" disabled={busy}>
          {mode === "login" ? "Войти" : "Создать аккаунт"}
        </button>
        <a className="sso-btn" href="/api/v1/auth/sso/login">
          Войти через корпоративный SSO
        </a>
      </form>
    </div>
  );
}
