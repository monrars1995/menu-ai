"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import { formatCurrency, statusBadge } from "@/lib/utils";
import Link from "next/link";
import {
  ChefHat,
  BookOpen,
  UtensilsCrossed,
  Salad,
  TrendingUp,
} from "lucide-react";
import type { Cardapio } from "@/lib/types";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [stats, setStats] = useState<{ fichas: number; ingredientes: number }>({ fichas: 0, ingredientes: 0 });
  const [recentCardapios, setRecentCardapios] = useState<Cardapio[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    // Aguarda a autenticação terminar antes de buscar dados
    if (loading) return;

    setLoadingStats(true);
    Promise.all([
      api.info()
        .then((r) => setStats({ fichas: r.total_fichas ?? 0, ingredientes: r.total_ingredientes ?? 0 }))
        .catch(() => {}),
      api.cardapios.list("per_page=5")
        .then((r) => setRecentCardapios(r.items || []))
        .catch(() => {}),
    ]).finally(() => setLoadingStats(false));
  }, [loading, user]);

  const firstName = user?.nome?.split(" ")[0] || user?.email?.split("@")[0] || "Usuário";

  return (
    <div className="max-w-5xl">
      {/* Hero — whitespace band */}
      <div className="pb-8 pt-2">
        <h1 className="text-[32px] font-medium tracking-tight text-ink">
          Olá, {firstName}
        </h1>
        <p className="mt-2 text-sm text-ink-muted-48">
          Bem-vindo ao Menu.AI. Comece gerando um cardápio ou gerencie suas fichas.
        </p>
      </div>

      {/* Stat cards — banda signature (coral doc) para CTA principal */}
      <div className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/gerar"
          className="group flex items-center gap-4 rounded-xl border border-white/10 bg-signature-coral p-5 text-white transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/15">
            <ChefHat size={20} />
          </div>
          <div>
            <p className="text-sm font-medium">Gerar Cardápio</p>
            <p className="text-xs text-white/80">Crie com IA</p>
          </div>
        </Link>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-info/10 text-info">
            <BookOpen size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">{loadingStats ? <span className="inline-block w-6 h-5 rounded bg-surface-soft animate-pulse" /> : (stats.fichas ?? "—")}</p>
            <p className="text-xs text-ink-muted-48">Fichas Técnicas</p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
            <Salad size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">{loadingStats ? <span className="inline-block w-6 h-5 rounded bg-surface-soft animate-pulse" /> : (stats.ingredientes ?? "—")}</p>
            <p className="text-xs text-ink-muted-48">Ingredientes</p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
            <TrendingUp size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">{recentCardapios.length}</p>
            <p className="text-xs text-ink-muted-48">Cardápios Recentes</p>
          </div>
        </div>
      </div>

      {/* Recent cardapios — flat table */}
      <div className="rounded-xl border border-hairline/60 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
          <h2 className="text-base font-medium text-ink">Cardápios Recentes</h2>
          <Link href="/cardapios" className="text-sm font-medium text-link hover:underline">
            Ver todos
          </Link>
        </div>
        {recentCardapios.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-surface-soft text-ink-muted-48">
              <UtensilsCrossed size={24} />
            </div>
            <p className="text-sm text-ink-muted-48">Nenhum cardápio ainda</p>
            <Link href="/gerar" className="mt-4 text-sm font-medium text-link hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2">
              Criar primeiro cardápio →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-hairline">
            {recentCardapios.map((c) => {
              const badge = statusBadge(c.status);
              return (
                <Link key={c.id} href={`/cardapios/${c.id}`} className="flex items-center justify-between px-5 py-4 transition-colors hover:bg-surface-soft">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{c.nome}</p>
                    <p className="mt-0.5 text-xs text-ink-muted-48">
                      {c.periodo_inicio ? new Date(c.periodo_inicio).toLocaleDateString("pt-BR") : "—"}
                      {" · "}
                      {c.num_dias ?? "—"} dias
                      {c.custo_medio_dia ? ` · ${formatCurrency(c.custo_medio_dia)}/dia` : ""}
                    </p>
                  </div>
                  <span className={`ml-3 rounded-md px-2 py-0.5 text-[10px] font-semibold ${
                    badge.variant === "success" ? "bg-success/10 text-success border border-success-border/30" :
                    badge.variant === "warning" ? "bg-amber-50 text-amber-800 border border-amber-200" :
                    badge.variant === "destructive" ? "bg-red-50 text-red-700 border border-red-200" :
                    badge.variant === "default" ? "bg-primary-subtle text-ink border border-hairline" :
                    "bg-surface-soft text-ink-muted-48 border border-hairline"
                  }`}>
                    {badge.label}
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
