"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { Cardapio } from "@/lib/types";
import { formatCurrency, formatDate, statusBadge } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineLoader } from "@/components/ui/loading";
import { UtensilsCrossed, Search, Filter } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "rascunho", label: "Rascunho" },
  { value: "em_revisao", label: "Em Revisão" },
  { value: "aprovado", label: "Aprovado" },
  { value: "publicado", label: "Publicado" },
  { value: "arquivado", label: "Arquivado" },
];

export default function CardapiosPage() {
  const router = useRouter();
  const [cardapios, setCardapios] = useState<Cardapio[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { const r = await api.cardapios.list(); setCardapios(r.items || []); } catch {}
    setLoading(false);
  }

  const filtered = cardapios.filter((c) => {
    const ms = c.nome.toLowerCase().includes(search.toLowerCase());
    const mst = !statusFilter || c.status === statusFilter;
    return ms && mst;
  });

  const columns: Column<Cardapio>[] = [
    { key: "nome", header: "Nome", render: (c) => <span className="font-medium">{c.nome}</span> },
    { key: "periodo", header: "Período", render: (c) => (
      <span className="text-xs">
        {c.periodo_inicio ? formatDate(c.periodo_inicio) : "—"} — {c.periodo_fim ? formatDate(c.periodo_fim) : "—"}
      </span>
    )},
    { key: "dias", header: "Dias", render: (c) => c.num_dias || "—" },
    { key: "custo", header: "Custo/dia", render: (c) => c.custo_medio_dia != null ? formatCurrency(c.custo_medio_dia) : "—" },
    { key: "status", header: "Status", render: (c) => <StatusBadge status={c.status} /> },
    { key: "created", header: "Criado", render: (c) => <span className="text-xs text-ink-muted-48">{formatDate(c.created_at)}</span> },
  ];

  return (
    <div>
      <PageHeader title="Cardápios" description="Visualize e gerencie os cardápios gerados" actions={<Button onClick={() => router.push("/gerar")} size="sm"><UtensilsCrossed size={16} />Gerar Novo</Button>} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted-48" />
          <input type="text" placeholder="Buscar cardápios…" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-hairline bg-white py-2 pl-8 pr-3 text-sm placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]">
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      <div className="rounded-lg border border-hairline bg-white">
        {loading ? (
          <div className="py-12 text-center"><InlineLoader text="Carregando…" /></div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={UtensilsCrossed} title="Nenhum cardápio encontrado" description="Gere um cardápio com IA para começar" actionLabel="Gerar Cardápio" actionHref="/gerar" />
        ) : (
          <Table columns={columns} data={filtered} keyExtractor={(c) => c.id} onRowClick={(c) => router.push(`/cardapios/${c.id}`)} />
        )}
      </div>
    </div>
  );
}
