"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import type { Contrato, ContratoAnalise, GramaturaConferencia } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PageHeader } from "@/components/layout/page-header";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineLoader } from "@/components/ui/loading";
import {
  Plus, FileText, Upload, Pencil, Trash2, Search,
  ChevronRight, AlertTriangle, CheckCircle2, TrendingUp,
  ChevronDown, ChevronRight as ChevronRightIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";

/* ---------- helpers ---------- */

function TagList({ items, color }: { items: string[]; color?: string }) {
  if (!items?.length) return <p className="text-xs text-ink-muted-48 italic">Nenhum</p>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((t, i) => (
        <span key={i} className={`rounded-md border px-2.5 py-0.5 text-xs font-medium ${color ?? "bg-surface-soft text-ink-muted-80 border-hairline"}`}>
          {t}
        </span>
      ))}
    </div>
  );
}

function SectionCard({ title, icon: Icon, children, defaultOpen = true }: {
  title: string; icon?: any; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-hairline bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-ink">
          {Icon && <Icon size={14} className="text-ink" />}
          {title}
        </span>
        {open ? <ChevronDown size={14} className="text-ink-muted-48" /> : <ChevronRightIcon size={14} className="text-ink-muted-48" />}
      </button>
      {open && <div className="border-t border-hairline px-4 py-3">{children}</div>}
    </div>
  );
}

/* ---------- page ---------- */

export default function ContratosPage() {
  const router = useRouter();
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Contrato | null>(null);
  const [deleting, setDeleting] = useState<Contrato | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);

  const [form, setForm] = useState({ nome: "", numero_contrato: "", data_inicio: "", data_fim: "", custo_total_max: "", observacoes: "" });

  // Detail / analysis state
  const [selected, setSelected] = useState<Contrato | null>(null);
  const [analise, setAnalise] = useState<ContratoAnalise | null>(null);
  const [loadingAnalise, setLoadingAnalise] = useState(false);
  const [gramatura, setGramatura] = useState<GramaturaConferencia | null>(null);
  const [loadingGramatura, setLoadingGramatura] = useState(false);
  const [showAnalise, setShowAnalise] = useState(false);

  useEffect(() => { loadContratos(); }, []);

  async function loadContratos() {
    setLoading(true);
    try { const r = await api.contratos.list(); setContratos(r.items || []); } catch {}
    setLoading(false);
  }

  function openCreate() {
    setForm({ nome: "", numero_contrato: "", data_inicio: "", data_fim: "", custo_total_max: "", observacoes: "" });
    setEditing(null);
    setShowCreate(true);
  }

  function openEdit(c: Contrato) {
    setForm({
      nome: c.nome || "",
      numero_contrato: c.numero_contrato || "",
      data_inicio: c.data_inicio?.slice(0, 10) || "",
      data_fim: c.data_fim?.slice(0, 10) || "",
      custo_total_max: c.custo_total_max?.toString() || "",
      observacoes: c.observacoes || "",
    });
    setEditing(c);
    setShowCreate(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const data = {
        nome: form.nome,
        numero_contrato: form.numero_contrato || undefined,
        data_inicio: form.data_inicio || undefined,
        data_fim: form.data_fim || undefined,
        custo_total_max: form.custo_total_max ? parseFloat(form.custo_total_max) : undefined,
        observacoes: form.observacoes || undefined,
      };
      if (editing) {
        await api.contratos.update(editing.id, data);
      } else {
        await api.contratos.create(data);
      }
      setShowCreate(false);
      await loadContratos();
    } catch (e: any) {
      alert(e.message || "Erro ao salvar contrato");
    }
    setSaving(false);
  }

  async function handleDelete() {
    if (!deleting) return;
    setSaving(true);
    try {
      await api.contratos.update(deleting.id, { ativo: false } as any);
      setDeleting(null);
      await loadContratos();
    } catch (e: any) {
      alert(e.message || "Erro ao desativar contrato");
    }
    setSaving(false);
  }

  async function handleUpload(id: string, file: File) {
    setUploading(id);
    try { await api.contratos.upload(id, file); await loadContratos(); }
    catch (e: any) { alert(e.message || "Erro no upload"); }
    setUploading(null);
  }

  async function loadAnalise(c: Contrato) {
    setSelected(c);
    setAnalise(null);
    setGramatura(null);
    setShowAnalise(true);
    setLoadingAnalise(true);
    try {
      const a = await api.contratos.analise(c.id);
      setAnalise(a);
    } catch { setAnalise(null); }
    setLoadingAnalise(false);
  }

  async function loadGramatura() {
    if (!selected) return;
    setLoadingGramatura(true);
    try {
      const g = await api.fichas.conferenciaGramatura(selected.id);
      setGramatura(g);
    } catch { setGramatura(null); }
    setLoadingGramatura(false);
  }

  const filtered = contratos.filter((c) =>
    c.nome.toLowerCase().includes(search.toLowerCase()) ||
    (c.numero_contrato || "").toLowerCase().includes(search.toLowerCase())
  );

  const columns: Column<Contrato>[] = [
    { key: "nome", header: "Nome", render: (c) => <span className="font-medium">{c.nome}</span> },
    { key: "numero_contrato", header: "Nº Contrato", render: (c) => c.numero_contrato || "—" },
    { key: "periodo", header: "Período", render: (c) => (
      <span className="text-xs">
        {c.data_inicio ? formatDate(c.data_inicio) : "—"} — {c.data_fim ? formatDate(c.data_fim) : "—"}
      </span>
    )},
    { key: "custo_total_max", header: "Custo Máx.", render: (c) => c.custo_total_max != null ? `R$ ${c.custo_total_max.toLocaleString("pt-BR")}` : "—" },
    { key: "status", header: "Status", render: (c) => <StatusBadge status={c.ativo ? "aprovado" : "arquivado"} /> },
    { key: "actions", header: "", className: "text-right", render: (c) => (
      <div className="flex items-center justify-end gap-1">
        <label className="cursor-pointer rounded-md p-1 text-ink-muted-48 hover:bg-surface-soft hover:text-ink" title="Upload PDF">
          {uploading === c.id ? <span className="text-xs">Enviando…</span> : <Upload size={14} />}
          <input type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(c.id, f); }} />
        </label>
        <button onClick={() => openEdit(c)} className="rounded-md p-1 text-ink-muted-48 hover:bg-surface-soft hover:text-ink"><Pencil size={14} /></button>
        <button onClick={() => setDeleting(c)} className="rounded-md p-1 text-ink-muted-48 hover:bg-red-50 hover:text-red-600"><Trash2 size={14} /></button>
        <button onClick={() => loadAnalise(c)} className="rounded-md p-1 text-link hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border" title="Ver análise"><ChevronRight size={14} /></button>
      </div>
    )},
  ];

  /* ---------- Analysis panel ---------- */

  function renderAnalisePanel() {
    if (!showAnalise || !selected) return null;

    return (
      <div className="fixed inset-y-0 right-0 z-40 w-full max-w-xl bg-white shadow-2xl border-l border-hairline overflow-y-auto">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-hairline bg-white px-5 py-3">
          <div>
            <h2 className="text-[20px] font-medium text-ink">{selected.nome}</h2>
            <p className="text-xs text-ink-muted-48">Análise do contrato</p>
          </div>
          <button onClick={() => setShowAnalise(false)} className="rounded-md p-1.5 text-ink-muted-48 hover:bg-surface-soft">
            ✕
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* PDF Upload */}
          <SectionCard title="Arquivo do Contrato" icon={FileText}>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink-muted-80 hover:bg-surface-soft hover:text-ink">
                <Upload size={14} />
                {selected.arquivo_path ? selected.arquivo_path.split("/").pop() : "Upload PDF / XLSX"}
                <input type="file" accept=".pdf,.xlsx,.xls" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(selected.id, f); }} />
              </label>
              {uploading === selected.id && <InlineLoader text="Enviando…" />}
              {selected.arquivo_path && (
                <span className="flex items-center gap-1 text-xs text-green-700">
                  <CheckCircle2 size={12} /> Enviado
                </span>
              )}
            </div>
          </SectionCard>

          {/* Analysis report */}
          {loadingAnalise && <InlineLoader text="Carregando análise…" />}

          {analise && analise.status !== "nao_analisado" && (
            <>
              <SectionCard title="Necessidades do Contrato" icon={FileText} defaultOpen={false}>
                <p className="text-sm text-ink-muted-80 whitespace-pre-wrap">{analise.necessidades?.observacoes || "—"}</p>
                {analise.necessidades?.num_refeicoes_dia && (
                  <p className="mt-2 text-xs text-ink-muted-48">
                    Refeições/dia: {analise.necessidades.num_refeicoes_dia}
                  </p>
                )}
              </SectionCard>

              <SectionCard title="Servicos" icon={CheckCircle2} defaultOpen={false}>
                {analise.servicos?.num_refeicoes_dia && (
                  <p className="text-sm text-ink-muted-80">
                    Nº refeições/dia: <strong>{analise.servicos.num_refeicoes_dia}</strong>
                  </p>
                )}
                {analise.servicos?.estrutura && (
                  <div className="mt-2 text-sm text-ink-muted-80">
                    <p className="text-xs font-medium text-ink-muted-48 mb-1">Estrutura:</p>
                    <pre className="text-xs bg-surface-soft rounded-md p-2 overflow-x-auto">
                      {JSON.stringify(analise.servicos.estrutura, null, 2)}
                    </pre>
                  </div>
                )}
              </SectionCard>

              <SectionCard title="Gramaturas por Categoria" icon={TrendingUp}>
                {analise.gramaturas && Object.keys(analise.gramaturas).length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(analise.gramaturas).map(([cat, val]) => (
                      <div key={cat} className="rounded-md border border-hairline bg-surface-soft px-3 py-2">
                        <p className="text-xs font-medium text-ink-muted-48">{cat}</p>
                        <p className="text-sm font-medium text-ink">{val}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-ink-muted-48 italic">Nenhuma gramatura extraída</p>
                )}
              </SectionCard>

              <SectionCard title="Incidências" icon={AlertTriangle} defaultOpen={false}>
                <TagList items={analise.incidencias} color="bg-amber-50 text-amber-800 border-amber-200" />
              </SectionCard>

              <SectionCard title="Proibições" icon={AlertTriangle} defaultOpen={false}>
                <TagList items={analise.proibicoes} color="bg-red-50 text-red-800 border-red-200" />
              </SectionCard>

              <div className="grid grid-cols-2 gap-4">
                <SectionCard title="Dietas Especiais" defaultOpen={false}>
                  <TagList items={analise.dietas_especiais} color="bg-blue-50 text-blue-800 border-blue-200" />
                </SectionCard>
                <SectionCard title="Alergenos" defaultOpen={false}>
                  <TagList items={analise.restricoes_alergenos} color="bg-orange-50 text-orange-800 border-orange-200" />
                </SectionCard>
              </div>

              <SectionCard title="Sazonalidade Obrigatoria" defaultOpen={false}>
                <TagList items={analise.sazonalidade} />
              </SectionCard>

              {/* Gramatura conferencia */}
              <div className="pt-2">
                <button
                  onClick={loadGramatura}
                  disabled={loadingGramatura}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2 disabled:opacity-50"
                >
                  <TrendingUp size={14} />
                  {loadingGramatura ? "Calculando…" : "Conferir Gramatura vs Fichas"}
                </button>
              </div>

              {gramatura && (
                <SectionCard title={`Conferencia de Gramatura (${gramatura.conformes}/${gramatura.total} conformes)`}>
                  {/* Summary */}
                  <div className="flex gap-3 mb-3">
                    <span className="rounded-md border bg-green-50 px-3 py-1 text-xs font-medium text-green-700 border-green-200">
                      {gramatura.conformes} Conforme
                    </span>
                    <span className="rounded-md border bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700 border-yellow-200">
                      {gramatura.nao_conformes} Não conforme
                    </span>
                    <span className="rounded-md border bg-surface-soft px-3 py-1 text-xs font-medium text-ink-muted-48 border-hairline">
                      {gramatura.sem_dado} Sem dado
                    </span>
                  </div>
                  {/* Table */}
                  <div className="table-wrap overflow-x-auto">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr className="border-b border-hairline">
                          <th className="py-1.5 px-2 text-left font-medium text-ink-muted-48">Ficha</th>
                          <th className="py-1.5 px-2 text-left font-medium text-ink-muted-48">Categoria</th>
                          <th className="py-1.5 px-2 text-right font-medium text-ink-muted-48">Peso Ficha (g)</th>
                          <th className="py-1.5 px-2 text-right font-medium text-ink-muted-48">Contrato (g)</th>
                          <th className="py-1.5 px-2 text-right font-medium text-ink-muted-48">Dif. (g)</th>
                          <th className="py-1.5 px-2 text-right font-medium text-ink-muted-48">Dif. (%)</th>
                          <th className="py-1.5 px-2 text-center font-medium text-ink-muted-48">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gramatura.itens.map((item, i) => (
                          <tr key={i} className="border-b border-hairline">
                            <td className="py-1.5 px-2 font-medium text-ink">{item.ficha}</td>
                            <td className="py-1.5 px-2 text-ink-muted-80">{item.categoria}</td>
                            <td className="py-1.5 px-2 text-right">{item.peso_ficha ?? "—"}</td>
                            <td className="py-1.5 px-2 text-right">{item.gramatura_contrato ?? "—"}</td>
                            <td className={`py-1.5 px-2 text-right ${
                              (item.diferenca_g ?? 0) < 0 ? "text-red-600" : (item.diferenca_g ?? 0) > 0 ? "text-amber-600" : "text-green-600"
                            }`}>{item.diferenca_g != null ? item.diferenca_g.toFixed(1) : "—"}</td>
                            <td className="py-1.5 px-2 text-right">{item.diferenca_pct != null ? `${item.diferenca_pct.toFixed(1)}%` : "—"}</td>
                            <td className="py-1.5 px-2 text-center">
                              <span className={`rounded-md border px-2 py-0.5 text-[10px] font-medium ${
                                item.status === "ok" ? "bg-green-50 text-green-700 border-green-200" :
                                item.status === "abaixo" ? "bg-yellow-50 text-yellow-700 border-yellow-200" :
                                item.status === "acima" ? "bg-red-50 text-red-700 border-red-200" :
                                "bg-surface-soft text-ink-muted-48 border-hairline"
                              }`}>
                                {item.status === "ok" ? "Conforme" :
                                 item.status === "abaixo" ? "Abaixo" :
                                 item.status === "acima" ? "Acima" : "Sem dado"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </SectionCard>
              )}
            </>
          )}

          {analise && analise.status === "nao_analisado" && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm text-amber-800">
                Contrato ainda não analisado. O agente analisa o contrato durante a geração do cardápio.
              </p>
              <p className="mt-1 text-xs text-amber-700">
                Faça upload do PDF e gere um cardápio para disparar a análise.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ---------- render ---------- */

  return (
    <div>
      <PageHeader
        title="Contratos"
        description="Gerencie contratos e regras de alimentação"
        actions={<Button onClick={openCreate} size="sm"><Plus size={16} />Novo Contrato</Button>}
      />

      <div className="mb-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted-48" />
          <input
            type="text" placeholder="Buscar contratos…" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-hairline bg-white py-2 pl-8 pr-3 text-sm placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
          />
        </div>
      </div>

      <div className="rounded-lg border border-hairline bg-white">
        {loading ? (
          <div className="py-12 text-center"><InlineLoader text="Carregando contratos…" /></div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={FileText} title="Nenhum contrato encontrado" description="Crie um contrato para definir regras de alimentação" actionLabel="Novo Contrato" onAction={openCreate} />
        ) : (
          <Table columns={columns} data={filtered} keyExtractor={(c) => c.id} onRowClick={(c) => loadAnalise(c)} />
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={editing ? "Editar Contrato" : "Novo Contrato"} size="lg">
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted-80">Nome *</label>
            <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} required
              className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted-80">Nº Contrato</label>
              <input value={form.numero_contrato} onChange={(e) => setForm({ ...form, numero_contrato: e.target.value })}
                className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted-80">Custo Total Máx. (R$)</label>
              <input type="number" step="0.01" value={form.custo_total_max} onChange={(e) => setForm({ ...form, custo_total_max: e.target.value })}
                className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted-80">Data Início</label>
              <input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
                className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted-80">Data Fim</label>
              <input type="date" value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
                className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted-80">Observações</label>
            <textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} rows={3}
              className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowCreate(false)}>Cancelar</Button>
            <Button size="sm" onClick={handleSave} disabled={saving || !form.nome}>{saving ? "Salvando…" : "Salvar"}</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={handleDelete}
        title="Desativar contrato" message={`Tem certeza que deseja desativar o contrato "${deleting?.nome}"?`}
        confirmLabel="Desativar" danger loading={saving} />

      {/* Analysis slide-over panel */}
      {renderAnalisePanel()}
    </div>
  );
}
