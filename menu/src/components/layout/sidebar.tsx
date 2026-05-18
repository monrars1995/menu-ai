"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  BookOpen,
  UtensilsCrossed,
  Salad,
  ChefHat,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useMobileNav } from "@/components/layout/mobile-nav";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/gerar", label: "Gerar Cardápio", icon: ChefHat },
  { href: "/cardapios", label: "Cardápios", icon: UtensilsCrossed },
  { href: "/fichas", label: "Fichas Técnicas", icon: BookOpen },
  { href: "/contratos", label: "Contratos", icon: FileText },
  { href: "/ingredientes", label: "Ingredientes", icon: Salad },
];

export function Sidebar({
  id,
  collapsed = false,
  onToggleCollapse,
}: {
  id?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { open, closeNav } = useMobileNav();

  return (
    <aside
      id={id}
      className={cn(
        "fixed left-0 top-0 z-[45] flex h-screen flex-col border-r border-hairline bg-white",
        "transition-[transform,width] duration-200 ease-out",
        "pt-[max(0px,env(safe-area-inset-top))] pb-[max(0px,env(safe-area-inset-bottom))]",
        collapsed ? "w-[76px]" : "w-60",
        open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}
    >
      {/* Logo */}
      <div className={cn("flex h-16 items-center border-b border-hairline px-3.5", collapsed ? "justify-center" : "gap-2")}>
        <img src="/isotipo.svg" alt="Menu.AI" className="h-8 w-8" />
        {!collapsed && <span className="text-base font-semibold tracking-tight text-ink">enu.AI</span>}
        <button
          type="button"
          onClick={onToggleCollapse}
          className={cn(
            "hidden h-8 w-8 items-center justify-center rounded-full border border-hairline bg-white text-ink-muted-48 transition-colors hover:bg-surface-soft hover:text-ink md:flex",
            collapsed ? "" : "ml-auto"
          )}
          title={collapsed ? "Expandir sidebar" : "Recolher sidebar"}
          aria-label={collapsed ? "Expandir sidebar" : "Recolher sidebar"}
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className={cn("flex-1 space-y-1 overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={() => closeNav()}
              className={cn(
                "flex items-center rounded-lg py-2.5 text-sm font-medium",
                collapsed ? "justify-center px-2" : "gap-2.5 px-3",
                "transition-all duration-200 ease-out",
                active
                  ? "bg-surface-soft text-ink ring-1 ring-hairline"
                  : "text-ink-muted-48 hover:bg-surface-soft hover:text-ink hover:translate-x-0.5"
              )}
              title={collapsed ? label : undefined}
            >
              <Icon size={16} strokeWidth={active ? 2 : 1.5} className="transition-transform duration-200" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>

      {/* User + version */}
      <div className="border-t border-hairline p-3">
        {user && (
          <div className={cn("mb-2 flex items-center rounded-md px-2 py-1.5", collapsed ? "justify-center" : "gap-2")}>
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-strong text-xs font-medium text-ink-muted-80">
              {user.nome?.charAt(0) || user.email?.charAt(0) || "?"}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-ink">{user.nome || user.email}</p>
                <p className="truncate text-[10px] text-ink-muted-48">{user.role}</p>
              </div>
            )}
          </div>
        )}
        <button
          type="button"
          onClick={() => {
            closeNav();
            logout();
          }}
          className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-xs font-medium text-ink-muted-48 transition-all duration-200 hover:bg-surface-soft hover:text-ink"
          title={collapsed ? "Sair" : undefined}
        >
          <LogOut size={14} />
          {!collapsed && "Sair"}
        </button>
        {!collapsed && (
          <div className="mt-2 px-2 text-[10px] text-ink-muted-48/40 select-none">
            v3.6.6
          </div>
        )}
      </div>
    </aside>
  );
}
