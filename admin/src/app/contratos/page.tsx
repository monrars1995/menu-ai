"use client";

import { useCallback, useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, ChevronDown, ChevronRight, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

// --- Types ---
interface Contrato {
  id: string;
  nome: string;
  numero_contrato?: string;
  ativo: boolean;
  empresa_id: string;
  arquivo_path?: string;
  num_refeicoes_dia?: number;
  estrutura_refeicao?: string;
  observacoes?: string;
  regras_json?: Record<string, unknown>;
  gramaturas_json?: Record<string, string>;
}

interface AnaliseContrato {
  contrato_id: string;
  status: string;
  nome_contrato?: string;
  necessidades?: Record<string, unknown>;
  servicos?: Record<string, unknown>;
  incidencias?: unknown[];
  gramaturas?: Record<string, string>;
  proibicoes?: unknown[];
  restricoes_alergenos?: unknown[];
  dietas_especiais?: unknown[];
  sazonalidade?: unknown[];
  mensagem?: string;
}

interface GramaturaItem {
  ficha_id: string;
  nome: string;
  categoria: string;
  peso_ficha_g: number | null;
  gramatura_contrato_g: number | null;
  diferenca_g: number | null;
  diferenca_pct: number | null;
  status: string;
}

interface GramaturaResult {
  status: string;
  total: number;
  conformes: number;
  nao_conformes: number;
  sem_dado: number;
  itens: GramaturaItem[];
  mensagem?: string;
}

// --- Helpers ---
function statusBadge(status: string) {
  const map: Record<string, { cls: string; label: string }> = {
    ok: { cls: "badge-success", label: "Conforme" },
    abaixo: { cls: "badge-warning", label: "Abaixo" },
    acima: { cls: "badge-danger", label: "Acima" },
    sem_dado: { cls: "badge-default", label: "Sem dado" },
  };
  const s = map[status] || map.sem_dado;
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}

function statusIcon(status: string) {
  if (status === "ok") return <CheckCircle size={14} className="text-green-600" />;
  if (status === "abaixo") return <ArrowDownRight size={14} className="text-yellow-600" />;
  if (status === "acima") return <ArrowUpRight size={14} className="text-red-600" />;
  return <Minus size={14} style={{ color: "var(--text-quaternary)" }} />;
}

// --- Section Card ---
function SectionCard({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="surface">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-5 py-3 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        <span>{title}</span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && <div className="border-t px-5 py-4" style={{ borderColor: "var(--color-hairline)" }}>{children}</div>}
    </div>
  );
}

function TagList({ items }: { items: unknown[] }) {
  if (!items || items.length === 0) return <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>Nenhum item.</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((t, i) => (
        <span key={i} className="rounded-md px-2.5 py-1 text-xs" style={{ background: "var(--surface-subtle)", color: "var(--text-primary)" }}>{String(t)}</span>
      ))}
    </div>
  );
}

// --- Main Page ---
export default function ContratosPage() {
  const { apiFetch } = useApi();
  const auth = useAuth();
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Contrato | null>(null);
  const [analise, setAnalise] = useState<AnaliseContrato | null>(null);
  const [gramatura, setGramatura] = useState<GramaturaResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [loadingAnalise, setLoadingAnalise] = useState(false);
  const [loadingGramatura, setLoadingGramatura] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  async function loadContratos() {
    setLoading(true);
    const res = await apiFetch("/api/contratos/?skip=0&limit=200");
    if (res.ok) {
      const data = await res.json();
      setContratos(Array.isArray(data.items) ? data.items : []);
    }
    setLoading(false);
  }

  useEffect(() => { loadContratos(); }, []);

  async function loadAnalise(id: string) {
    setLoadingAnalise(true);
    setAnalise(null);
    const res = await apiFetch(`/api/contratos/${id}/analise`);
    if (res.ok) setAnalise(await res.json());
    setLoadingAnalise(false);
  }

  async function loadGramatura(id: string) {
    setLoadingGramatura(true);
    setGramatura(null);
    const res = await apiFetch(`/api/fichas-tecnicas/conferencia-gramatura?contrato_id=${id}`);
    if (res.ok) setGramatura(await res.json());
    setLoadingGramatura(false);
  }

  const selectContrato = useCallback((c: Contrato) => {
    setSelected(c);
    loadAnalise(c.id);
    loadGramatura(c.id);
  }, []);

  async function handleUpload(file: File) {
    if (!selected) return;
    setUploading(true);
    setUploadMsg("");
    const fd = new FormData();
    fd.append("file", file);
    const res = await apiFetch(`/api/contratos/${selected.id}/upload`, { method: "POST", body: fd });
    setUploading(false);
    if (res.ok) {
      setUploadMsg("Upload realizado com sucesso!");
      loadContratos();
      const ext = file.name.slice(file.name.lastIndexOf("."));
      selectContrato({ ...selected, arquivo_path: `/data/uploads/contratos/${selected.id}${ext}` });
    } else {
      const text = await res.text();
      setUploadMsg(`Erro: ${text || res.status}`);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) handleUpload(e.dataTransfer.files[0]);
  }

  return (
    <div className="flex gap-6">
      {/* Sidebar: Lista de contratos */}
      <div className="w-72 shrink-0">
        <h1 className="text-page-title mb-1">Contratos</h1>
        <p className="text-subtitle mb-4">Upload e análise de contratos</p>
        {loading ? (
          <div className="flex h-32 items-center justify-center"><Loader2 size={16} className="animate-spin" style={{ color: "var(--color-primary)" }} /></div>
        ) : (
          <div className="space-y-1">
            {contratos.map((c) => (
              <button
                key={c.id}
                onClick={() => selectContrato(c)}
                className={`w-full rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                  selected?.id === c.id ? "font-medium" : "hover:bg-[var(--surface-subtle)]"
                }`}
                style={selected?.id === c.id ? { background: "var(--color-primary-subtle)", color: "var(--color-primary)" } : { color: "var(--text-primary)" }}
              >
                <div>{c.nome}</div>
                <div className="text-xs" style={{ color: selected?.id === c.id ? "var(--color-primary)" : "var(--text-tertiary)" }}>
                  {c.numero_contrato || "Sem número"} {c.arquivo_path ? "· PDF" : "· Sem arquivo"}
                </div>
              </button>
            ))}
            {contratos.length === 0 && <p className="px-3 py-4 text-center text-sm" style={{ color: "var(--text-tertiary)" }}>Nenhum contrato cadastrado.</p>}
          </div>
        )}
      </div>

      {/* Main: Detalhes do contrato */}
      <div className="min-w-0 flex-1">
        {!selected ? (
          <div className="flex h-64 items-center justify-center text-sm" style={{ color: "var(--text-tertiary)" }}>Selecione um contrato para ver detalhes.</div>
        ) : (
          <div className="space-y-5">
            <div>
              <h1 className="text-page-title">{selected.nome}</h1>
              <p className="text-subtitle">{selected.numero_contrato || "Sem número"} · {selected.ativo ? "Ativo" : "Inativo"}</p>
            </div>

            {/* Upload PDF */}
            <SectionCard title="Arquivo do Contrato (PDF)">
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
                  dragOver ? "border-[var(--color-primary)]" : "border-[var(--color-hairline-strong)]"
                }`}
                style={dragOver ? { background: "var(--color-primary-subtle)" } : {}}
              >
                <Upload size={24} style={{ color: "var(--text-tertiary)" }} className="mb-2" />
                <p className="mb-1 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Arraste um arquivo ou clique para selecionar</p>
                <p className="mb-3 text-xs" style={{ color: "var(--text-tertiary)" }}>PDF, XLSX ou XLS</p>
                <label className="cursor-pointer rounded-md px-4 py-2 text-sm font-medium text-white" style={{ background: "var(--color-primary)" }}>
                  Selecionar arquivo
                  <input
                    type="file"
                    accept=".pdf,.xlsx,.xls"
                    className="hidden"
                    onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
                  />
                </label>
                {uploading && <Loader2 size={16} className="mt-2 animate-spin" style={{ color: "var(--text-tertiary)" }} />}
                {uploadMsg && <p className="mt-2 text-xs text-green-600">{uploadMsg}</p>}
              </div>
              {selected.arquivo_path && (
                <p className="mt-2 flex items-center gap-1.5 text-xs" style={{ color: "var(--text-tertiary)" }}>
                  <FileText size={12} /> Arquivo vinculado: <code className="rounded px-1.5 py-0.5 text-xs" style={{ background: "var(--surface-subtle)" }}>{selected.arquivo_path.split("/").pop()}</code>
                </p>
              )}
            </SectionCard>

            {/* Relatório de Análise */}
            <SectionCard title="Relatório de Análise do Contrato">
              {loadingAnalise ? (
                <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-tertiary)" }}><Loader2 size={14} className="animate-spin" /> Carregando análise...</div>
              ) : analise ? (
                analise.status === "nao_analisado" ? (
                  <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>{analise.mensagem}</p>
                ) : (
                  <div className="space-y-4">
                    {/* Necessidades */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Necessidades do Contrato</h3>
                      <div className="rounded-lg p-3 text-sm" style={{ background: "var(--surface-subtle)", color: "var(--text-primary)" }}>
                        {(analise.necessidades?.observacoes as string) || "Nenhuma observação registrada."}
                      </div>
                    </div>
                    {/* Serviços */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Serviços</h3>
                      <div className="rounded-lg p-3 text-sm" style={{ background: "var(--surface-subtle)", color: "var(--text-primary)" }}>
                        <div>Refeições/dia: <strong>{(analise.servicos?.num_refeicoes_dia as number) ?? "—"}</strong></div>
                        <div>Estrutura: <strong>{(analise.servicos?.estrutura as string) || "—"}</strong></div>
                      </div>
                    </div>
                    {/* Gramaturas */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Gramaturas por Categoria</h3>
                      {analise.gramaturas && Object.keys(analise.gramaturas).length > 0 ? (
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                          {Object.entries(analise.gramaturas).map(([cat, val]) => (
                            <div key={cat} className="rounded-lg px-3 py-2 text-center" style={{ background: "var(--surface-subtle)" }}>
                              <div className="text-xs" style={{ color: "var(--text-tertiary)" }}>{cat}</div>
                              <div className="text-lg font-semibold" style={{ color: "var(--color-primary)" }}>{val}</div>
                            </div>
                          ))}
                        </div>
                      ) : <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>Gramaturas não definidas.</p>}
                    </div>
                    {/* Incidências */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Incidências</h3>
                      <TagList items={analise.incidencias || []} />
                    </div>
                    {/* Proibições */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Proibições</h3>
                      <TagList items={analise.proibicoes || []} />
                    </div>
                    {/* Dietas e Alergenos */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Dietas Especiais</h3>
                        <TagList items={analise.dietas_especiais || []} />
                      </div>
                      <div>
                        <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Restrições / Alérgenos</h3>
                        <TagList items={analise.restricoes_alergenos || []} />
                      </div>
                    </div>
                    {/* Sazonalidade */}
                    <div>
                      <h3 className="mb-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>Sazonalidade Obrigatória</h3>
                      <TagList items={analise.sazonalidade || []} />
                    </div>
                  </div>
                )
              ) : <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>Nenhuma análise disponível.</p>}
            </SectionCard>

            {/* Conferência de Gramatura */}
            <SectionCard title="Conferência de Gramatura vs Contrato">
              {loadingGramatura ? (
                <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-tertiary)" }}><Loader2 size={14} className="animate-spin" /> Calculando...</div>
              ) : gramatura ? (
                gramatura.status === "sem_gramaturas" ? (
                  <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>{gramatura.mensagem}</p>
                ) : (
                  <div>
                    <div className="mb-3 flex gap-4 text-xs" style={{ color: "var(--text-tertiary)" }}>
                      <span className="flex items-center gap-1"><CheckCircle size={12} className="text-green-600" /> {gramatura.conformes} conformes</span>
                      <span className="flex items-center gap-1"><AlertTriangle size={12} className="text-yellow-600" /> {gramatura.nao_conformes} não conformes</span>
                      <span>{gramatura.sem_dado} sem dado</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b" style={{ borderColor: "var(--color-hairline)" }}>
                            <th className="px-3 py-2 text-left text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Ficha</th>
                            <th className="px-3 py-2 text-left text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Categoria</th>
                            <th className="px-3 py-2 text-right text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Peso Ficha (g)</th>
                            <th className="px-3 py-2 text-right text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Contrato (g)</th>
                            <th className="px-3 py-2 text-right text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Dif. (g)</th>
                            <th className="px-3 py-2 text-right text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Dif. (%)</th>
                            <th className="px-3 py-2 text-center text-xs font-medium uppercase" style={{ color: "var(--text-tertiary)" }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {gramatura.itens.map((item) => (
                            <tr key={item.ficha_id} className="border-b" style={{ borderColor: "var(--color-hairline)" }}>
                              <td className="px-3 py-2" style={{ color: "var(--text-primary)" }}>{item.nome}</td>
                              <td className="px-3 py-2" style={{ color: "var(--text-tertiary)" }}>{item.categoria || "—"}</td>
                              <td className="px-3 py-2 text-right">{item.peso_ficha_g ?? "—"}</td>
                              <td className="px-3 py-2 text-right">{item.gramatura_contrato_g ?? "—"}</td>
                              <td className={`px-3 py-2 text-right ${item.diferenca_g && item.diferenca_g < 0 ? "text-yellow-600" : item.diferenca_g && item.diferenca_g > 0 ? "text-red-600" : ""}`}>
                                {item.diferenca_g != null ? (item.diferenca_g > 0 ? `+${item.diferenca_g}` : item.diferenca_g) : "—"}
                              </td>
                              <td className="px-3 py-2 text-right">{item.diferenca_pct != null ? `${item.diferenca_pct > 0 ? "+" : ""}${item.diferenca_pct}%` : "—"}</td>
                              <td className="px-3 py-2 text-center">
                                <span className="inline-flex items-center gap-1">{statusIcon(item.status)}{statusBadge(item.status)}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )
              ) : <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>Nenhuma conferência disponível.</p>}
            </SectionCard>
          </div>
        )}
      </div>
    </div>
  );
}
