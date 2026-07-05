"use client";

// Shared chrome for non-chat pages: top navigation + auth guard.

import { useEffect, useState } from "react";
import { api, auth, type Plan } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Чат" },
  { href: "/documents", label: "Документы" },
  { href: "/compliance", label: "Комплаенс" },
];

export default function PageShell({
  title,
  active,
  children,
}: {
  title: string;
  active: string;
  children: React.ReactNode;
}) {
  const [plan, setPlan] = useState<Plan | null>(null);

  useEffect(() => {
    if (!auth.token()) {
      window.location.href = "/login";
      return;
    }
    api.plan().then(setPlan).catch(() => setPlan(null));
  }, []);

  return (
    <div className="page">
      <header className="topnav">
        <div className="brand">
          Legal<span>OS</span>
        </div>
        <nav>
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className={l.href === active ? "active" : ""}>
              {l.label}
            </a>
          ))}
        </nav>
        <div className="topnav-right">
          {plan && <span className="badge">{plan.tier}</span>}
          <button className="link-btn" onClick={() => auth.logout()}>
            Выйти
          </button>
        </div>
      </header>
      <main className="page-body">
        <h1>{title}</h1>
        {children}
      </main>
    </div>
  );
}
