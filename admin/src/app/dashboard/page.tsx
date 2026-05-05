"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { Building2, FileText, Apple, BookOpen, ClipboardList, Activity, Cpu, BrainCircuit } from "lucide-react";

interface DashboardData {
  scope: string;
  empresa_id?: string;
  user: { id: string; nome?: string; email: string; role: string };
  counts: {
    empresas: number;
    contratos: number;
    ingredientes: number;
    fichas: number;
    cardapios: number;
    jobs: number;
    jobs_ativos: number;
  };
  llm: {
    provider?: string;
    default?: string;
    enabled_models: number;
    total_models: number;
  };
  knowledge: {
    chunks?: number;
    chunks_embedded?: number;
  };
}

interface StatCard {
  label: string;
  value: number | string;
  icon: React.ElementType;
  hint?: string;
}

export default function DashboardPage() {
  const { apiFetch } = useApi();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await apiFetch("/api/admin/meta/dashboard");
    if (!res.ok) {
      setError("Não foi possível carregar o dashboard.");
      return;
    }
    const json = await res.json();
    setData(json);
  }

  const cards: StatCard[] = [
    { label: "Empresas", value: data?.counts.empresas ?? 0, icon: Building2 },
    { label: "Contratos", value: data?.counts.contratos ?? 0, icon: FileText },
    { label: "Ingredientes", value: data?.counts.ingredientes ?? 0, icon: Apple },
    { label: "Fichas", value: data?.counts.fichas ?? 0, icon: BookOpen },
    { label: "Cardápios", value: data?.counts.cardapios ?? 0, icon: ClipboardList },
    { label: "Jobs ativos", value: data?.counts.jobs_ativos ?? 0, icon: Activity, hint: `${data?.counts.jobs ?? 0} total` },
    { label: "Modelos ativos", value: data?.llm.enabled_models ?? 0, icon: Cpu, hint: `${data?.llm.total_models ?? 0} catalogados` },
    { label: "Chunks vetoriais", value: data?.knowledge.chunks ?? 0, icon: BrainCircuit, hint: `${data?.knowledge.chunks_embedded ?? 0} com embedding` },
  ];

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-page-title">Dashboard</h1>
        <p className="text-subtitle">
          {data ? `${data.user.nome || data.user.email} · ${data.user.role}` : "Carregando…"}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-8 rounded-lg border border-white/10 bg-signature-coral px-5 py-4 text-white">
        <p className="text-sm font-medium">Painel administrativo</p>
        <p className="mt-1 max-w-2xl text-xs text-white/85">
          Visão consolidada de empresas, contratos, fichas e jobs — alinhado ao sistema de design Menu.AI.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <StatCardView key={c.label} card={c} />
        ))}
      </div>
    </div>
  );
}

function StatCardView({ card }: { card: StatCard }) {
  const Icon = card.icon;
  return (
    <div className="surface p-5">
      <div className="mb-3 flex items-center gap-2" style={{ color: "var(--text-tertiary)" }}>
        <Icon size={16} />
        <span className="label-section">{card.label}</span>
      </div>
      <div className="text-2xl font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
        {card.value}
      </div>
      {card.hint && (
        <div className="mt-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
          {card.hint}
        </div>
      )}
    </div>
  );
}
