"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
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
import { UtensilsCrossed, Search, ChefHat, Sparkles, ChevronLeft, ChevronRight } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "rascunho", label: "Rascunho" },
  { value: "em_revisao", label: "Em Revisão" },
  { value: "aprovado", label: "Aprovado" },
  { value: "publicado", label: "Publicado" },
  { value: "arquivado", label: "Arquivado" },
];

const PAGE_SIZE = 15;

export default function CardapiosPage() {
  const router = useRouter();
  const [cardapios, setCardapios] = useState<Cardapio[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Debounce da busca
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  // Resetar paginação ao buscar/filtrar
  useEffect(() => { setPage(1); }, [debouncedSearch, statusFilter]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setLoadError(null);
    try { const r = await api.cardapios.list(); setCardapios(r.items || []); }
    catch (e: any) { setLoadError(e?.message || "Não foi possível carregar os cardápios."); }
    setLoading(false);
  }

  const filtered = useMemo(() => cardapios.filter((c) => {
    const ms = c.nome.toLowerCase().includes(debouncedSearch.toLowerCase());
    const mst = !statusFilter || c.status === statusFilter;
    return ms && mst;
  }), [cardapios, debouncedSearch, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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
    <div className="space-y-4">
      <PageHeader title="Cardápios" description={`${filtered.length} cardápio${filtered.length !== 1 ? "s" : ""} encontrado${filtered.length !== 1 ? "s" : ""}`} actions={<Button onClick={() => router.push("/gerar")} size="sm"><UtensilsCrossed size={16} />Gerar Novo</Button>} />

      <div className="grid gap-3 rounded-lg border border-hairline bg-white p-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_220px]">
        <div className="relative min-w-0">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted-48" />
          <input type="text" placeholder="Buscar cardápios…" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-hairline bg-white py-2 pl-8 pr-3 text-sm placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]">
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {loadError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-hairline bg-white">
        {loading ? (
          <div className="py-12 text-center"><InlineLoader text="Carregando…" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-surface-soft to-hairline/30 text-ink-muted-48">
              <Sparkles size={28} />
            </div>
            <p className="text-sm font-medium text-ink">Nenhum cardápio encontrado</p>
            <p className="mt-1 max-w-xs text-xs text-ink-muted-48">
              Gere um cardápio completo com IA, otimizado por custo e nutrição para o seu serviço.
            </p>
            <button
              onClick={() => router.push("/gerar")}
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-signature-coral px-4 py-2 text-sm font-medium text-white transition-all duration-200 hover:opacity-90 hover:shadow-md"
            >
              <ChefHat size={16} />
              Gerar Cardápio
            </button>
          </div>
        ) : (
          <>
            <Table columns={columns} data={paginated} keyExtractor={(c) => c.id} onRowClick={(c) => router.push(`/cardapios/${c.id}`)} />

            {/* Paginação */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-hairline px-5 py-3">
                <p className="text-xs text-ink-muted-48">
                  {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} de {filtered.length}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-md p-1.5 text-ink-muted-48 transition-colors hover:bg-surface-soft hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="min-w-[3rem] text-center text-xs font-medium text-ink">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="rounded-md p-1.5 text-ink-muted-48 transition-colors hover:bg-surface-soft hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
