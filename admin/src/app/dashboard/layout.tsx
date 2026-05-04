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
  { href: "/fichas", label: "Fichas T\xc3\xa9cnicas", icon: BookOpen },
  { href: "/cardapios", label: "Card\xc3\xa1pios", icon: ClipboardList },
  { href: "/llm", label: "LLM", icon: Cpu },
  { href: "/knowledge", label: "Knowledge", icon: BrainCircuit },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();

  if (auth.loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--surface-canvas)]">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-primary)]" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--surface-canvas)]">
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r bg-white" style={{ borderColor: "var(--color-hairline)" }}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg" style={{ background: "var(--color-primary)" }}>
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight text-[var(--text-primary)]">Menu.AI</span>
          <span className="text-xs font-medium" style={{ color: "var(--color-primary)" }}>Admin</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-px px-3 py-2">
          {nav.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "font-medium"
                    : "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]"
                }`}
                style={active ? { background: "var(--color-primary-subtle)", color: "var(--color-primary)" } : {}}
              >
                <Icon size={16} strokeWidth={active ? 2 : 1.5} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="border-t px-5 py-4" style={{ borderColor: "var(--color-hairline)" }}>
          {auth.user && (
            <div className="mb-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
              <div className="font-medium" style={{ color: "var(--text-secondary)" }}>
                {auth.user.nome || auth.user.email}
              </div>
              <div>{auth.user.role}</div>
            </div>
          )}
          <button onClick={auth.logout} className="btn-secondary w-full text-xs">
            <LogOut size={14} className="mr-1.5" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex min-w-0 flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-6xl p-8">{children}</div>
      </main>
    </div>
  );
}
