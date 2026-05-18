"use client";

import { useEffect, useState, useMemo } from "react";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import { useBaseInfo } from "@/lib/base-info-context";
import { formatCurrency, statusBadge } from "@/lib/utils";
import Link from "next/link";
import {
  ChefHat,
  BookOpen,
  UtensilsCrossed,
  Salad,
  TrendingUp,
  FileText,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import type { Cardapio } from "@/lib/types";

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const { status: baseStatus, data: baseData, message: baseMessage } = useBaseInfo();
  const [recentCardapios, setRecentCardapios] = useState<Cardapio[]>([]);

  useEffect(() => {
    // Aguarda a autenticação terminar antes de buscar dados
    if (loading) return;

    api.cardapios
      .list("per_page=5")
      .then((r) => setRecentCardapios(r.items || []))
      .catch(() => {});
  }, [loading, user]);

  const firstName = user?.nome?.split(" ")[0] || user?.email?.split("@")[0] || "Usuário";
  const greeting = useMemo(() => getGreeting(), []);

  const SkeletonPulse = () => (
    <span className="inline-block w-8 h-6 rounded bg-surface-soft animate-pulse" />
  );

  return (
    <div>
      <div className="pb-5 pt-1">
        <h1 className="text-[28px] font-semibold tracking-tight text-ink">
          {greeting}, {firstName}
        </h1>
        <p
          className={`mt-2 inline-flex rounded-md border px-2 py-1 text-xs ${
            baseStatus === "error" ? "text-red-700" : "text-ink-muted-48"
          }`}
          title={baseMessage}
        >
          {baseStatus === "loading" ? "Carregando base..." : baseStatus === "error" ? "Base indisponível" : baseMessage}
        </p>
      </div>

      {/* Stat cards */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/gerar"
          className="group flex items-center gap-4 rounded-xl border border-white/10 bg-signature-coral p-5 text-white transition-all duration-200 hover:opacity-95 hover:shadow-lg hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/15">
            <ChefHat size={20} />
          </div>
          <div>
            <p className="text-sm font-medium">Gerar Cardápio</p>
            <p className="text-xs text-white/80">Crie com IA</p>
          </div>
        </Link>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-info/10 text-info">
            <BookOpen size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">
              {baseStatus === "loading" ? <SkeletonPulse /> : baseStatus === "error" ? "—" : (baseData.totalFichas ?? "—")}
            </p>
            <p className="text-xs text-ink-muted-48">Fichas Técnicas</p>
            <p className="mt-0.5 flex items-center gap-1 text-[10px] text-ink-muted-48/60">
              <TrendingUp size={10} className="text-success" />
              <span>na base atual</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
            <Salad size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">
              {baseStatus === "loading" ? <SkeletonPulse /> : baseStatus === "error" ? "—" : (baseData.totalIngredientes ?? "—")}
            </p>
            <p className="text-xs text-ink-muted-48">Ingredientes</p>
            <p className="mt-0.5 flex items-center gap-1 text-[10px] text-ink-muted-48/60">
              <TrendingUp size={10} className="text-success" />
              <span>na base atual</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-hairline/60 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
            <TrendingUp size={20} />
          </div>
          <div>
            <p className="text-2xl font-medium text-ink">{recentCardapios.length}</p>
            <p className="text-xs text-ink-muted-48">Cardápios Recentes</p>
          </div>
        </div>
      </div>

      {/* Quick-actions */}
      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { href: "/fichas", label: "Fichas Técnicas", icon: BookOpen, color: "text-info" },
          { href: "/ingredientes", label: "Ingredientes", icon: Salad, color: "text-success" },
          { href: "/contratos", label: "Contratos", icon: FileText, color: "text-amber-600" },
          { href: "/cardapios", label: "Cardápios", icon: UtensilsCrossed, color: "text-violet-600" },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="group flex items-center gap-3 rounded-lg border border-hairline/60 bg-white px-4 py-3 text-sm font-medium text-ink transition-all duration-200 hover:border-hairline hover:shadow-sm hover:-translate-y-0.5"
          >
            <item.icon size={16} className={item.color} />
            <span className="flex-1 truncate">{item.label}</span>
            <ArrowRight size={14} className="text-ink-muted-48/0 transition-all duration-200 group-hover:text-ink-muted-48 group-hover:translate-x-0.5" />
          </Link>
        ))}
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
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-surface-soft to-hairline/30 text-ink-muted-48">
              <Sparkles size={28} />
            </div>
            <p className="text-sm font-medium text-ink">Nenhum cardápio ainda</p>
            <p className="mt-1 max-w-xs text-xs text-ink-muted-48">
              Use a inteligência artificial para gerar cardápios completos, otimizados por custo e nutrição.
            </p>
            <Link href="/gerar" className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-signature-coral px-4 py-2 text-sm font-medium text-white transition-all duration-200 hover:opacity-90 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2">
              <ChefHat size={16} />
              Criar primeiro cardápio
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
