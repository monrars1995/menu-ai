"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard,
  Building2,
  FileText,
  Apple,
  BookOpen,
  ClipboardList,
  Cpu,
  BrainCircuit,
  Sparkles,
  LogOut,
} from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/empresas", label: "Empresas", icon: Building2 },
  { href: "/contratos", label: "Contratos", icon: FileText },
  { href: "/ingredientes", label: "Ingredientes", icon: Apple },
  { href: "/fichas", label: "Fichas Técnicas", icon: BookOpen },
  { href: "/cardapios", label: "Cardápios", icon: ClipboardList },
  { href: "/llm", label: "LLM", icon: Cpu },
  { href: "/knowledge", label: "Knowledge", icon: BrainCircuit },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();

  if (auth.loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--surface-canvas)]">
        <div
          className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-ink)]"
          aria-hidden
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--surface-canvas)]">
      <aside
        className="flex w-60 shrink-0 flex-col border-r border-[var(--color-hairline)] bg-white"
        aria-label="Navegação principal"
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-[var(--color-hairline)] px-5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "var(--color-brand)" }}
          >
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-base font-medium tracking-tight text-[var(--text-primary)]">Menu.AI</span>
          <span className="text-xs font-medium text-[var(--color-muted)]">Admin</span>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-3">
          {nav.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-sm transition-colors ${
                  active
                    ? "border-[var(--color-ink)] bg-[var(--surface-subtle)] font-medium text-[var(--color-ink)]"
                    : "border-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--color-ink)]"
                }`}
              >
                <Icon size={16} strokeWidth={active ? 2 : 1.5} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-[var(--color-hairline)] px-5 py-4">
          {auth.user && (
            <div className="mb-3 text-xs text-[var(--text-tertiary)]">
              <div className="font-medium text-[var(--text-secondary)]">
                {auth.user.nome || auth.user.email}
              </div>
              <div>{auth.user.role}</div>
            </div>
          )}
          <button type="button" onClick={auth.logout} className="btn-secondary w-full text-xs">
            <LogOut size={14} className="mr-1.5 inline" />
            Sair
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-[1280px] px-6 py-8 sm:px-12">{children}</div>
      </main>
    </div>
  );
}
