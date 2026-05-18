"use client";

import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileNavProvider, useMobileNav } from "@/components/layout/mobile-nav";
import { BaseInfoProvider, useBaseInfo } from "@/lib/base-info-context";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu } from "lucide-react";

function BaseSummaryChip({ className = "" }: { className?: string }) {
  const { status, message, title, data } = useBaseInfo();
  const tone =
    status === "ready"
      ? "border-hairline text-ink-muted-48"
      : status === "loading"
      ? "border-hairline text-ink-muted-48"
      : "border-red-200 text-red-700";
  const compactMessage =
    status === "ready"
      ? `${data.totalFichas}f • ${data.totalIngredientes}i`
      : status === "loading"
      ? "Base..."
      : "Indisponível";

  return (
    <div
      className={`inline-flex h-7 items-center rounded-md border bg-white px-2 text-[11px] font-medium ${tone} ${className}`}
      title={title}
      aria-label={message}
    >
      <span className="whitespace-nowrap">{compactMessage}</span>
    </div>
  );
}

function AppChrome({ children }: { children: React.ReactNode }) {
  const { open, closeNav, openNav } = useMobileNav();
  const { title } = useBaseInfo();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem("menuai_sidebar_collapsed");
    setSidebarCollapsed(saved === "1");
  }, []);

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem("menuai_sidebar_collapsed", next ? "1" : "0");
      }
      return next;
    });
  }

  return (
    <div className="flex min-h-screen min-h-[100dvh] bg-canvas">
      {open ? (
        <button
          type="button"
          aria-label="Fechar menu"
          className="fixed inset-0 z-[35] bg-black/40 md:hidden"
          onClick={closeNav}
        />
      ) : null}

      <header className="fixed left-0 right-0 top-0 z-[44] flex h-14 items-center gap-3 border-b border-hairline bg-white/95 px-4 backdrop-blur-sm md:hidden">
        <button
          type="button"
          onClick={openNav}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-ink hover:bg-surface-soft"
          aria-expanded={open}
          aria-controls="app-sidebar"
        >
          <Menu size={22} strokeWidth={1.75} />
        </button>
        <div className="flex min-w-0 items-center gap-2">
          <img src="/isotipo.svg" alt="" className="h-7 w-7 shrink-0" aria-hidden />
          <span className="truncate text-sm font-medium text-ink">Menu.AI</span>
        </div>
        <div className="ml-auto max-w-[52vw]" title={title}>
          <BaseSummaryChip className="max-w-full truncate" />
        </div>
      </header>

      <Sidebar id="app-sidebar" collapsed={sidebarCollapsed} onToggleCollapse={toggleSidebar} />
      <main className={`ml-0 flex w-full min-h-0 min-w-0 flex-1 flex-col px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-[calc(3.5rem+env(safe-area-inset-top,0px))] md:px-6 md:pb-8 md:pt-6 ${sidebarCollapsed ? "md:ml-[76px]" : "md:ml-60"}`}>
        <div className="mx-auto w-full max-w-[1320px]">
          <div className="mb-5 hidden items-center justify-end md:flex">
            <BaseSummaryChip />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="flex items-center gap-3">
          <img src="/isotipo.svg" alt="Menu.AI" className="h-8 w-8 animate-pulse" />
          <div className="h-4 w-20 animate-pulse rounded bg-ink/10" />
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <MobileNavProvider>
      <BaseInfoProvider>
        <AppChrome>{children}</AppChrome>
      </BaseInfoProvider>
    </MobileNavProvider>
  );
}
