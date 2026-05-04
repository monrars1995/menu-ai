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

export function Sidebar({ id }: { id?: string }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { open, closeNav } = useMobileNav();

  return (
    <aside
      id={id}
      className={cn(
        "fixed left-0 top-0 z-[45] flex h-screen w-60 flex-col border-r border-hairline bg-white",
        "transition-transform duration-200 ease-out",
        "pt-[max(0px,env(safe-area-inset-top))] pb-[max(0px,env(safe-area-inset-bottom))]",
        open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2.5 border-b border-hairline px-4">
        <img src="/isotipo.svg" alt="Menu.AI" className="h-8 w-8" />
        <span className="font-display text-base font-medium text-ink">Menu.AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={() => closeNav()}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/8 text-primary"
                  : "text-ink-muted-48 hover:bg-surface-soft hover:text-ink"
              )}
            >
              <Icon size={16} strokeWidth={active ? 2 : 1.5} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-hairline p-3">
        {user && (
          <div className="mb-2 flex items-center gap-2 rounded-md px-2 py-1.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-strong text-xs font-medium text-ink-muted-80">
              {user.nome?.charAt(0) || user.email?.charAt(0) || "?"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-ink">{user.nome || user.email}</p>
              <p className="truncate text-[10px] text-ink-muted-48">{user.role}</p>
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={() => {
            closeNav();
            logout();
          }}
          className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-xs font-medium text-ink-muted-48 transition-colors hover:bg-surface-soft hover:text-ink"
        >
          <LogOut size={14} />
          Sair
        </button>
      </div>
    </aside>
  );
}
