"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import type { Cardapio, CardapioComponente, CardapioRefeicao, CardapioRefeicaoGrupo } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import { ArrowLeft, Download, FileText, CheckCircle2, Send, Eye, Printer, FileSpreadsheet } from "lucide-react";

const TIPOS_REFEICAO: Record<string, string> = {
  cafe_manha: "Café da Manhã",
  lanche_manha: "Lanche da Manhã",
  almoco: "Almoço",
  lanche_tarde: "Lanche da Tarde",
  jantar: "Jantar",
  ceia: "Ceia",
};

function toComponent(ref: CardapioRefeicao): CardapioComponente {
  return {
    id: ref.id,
    tipo_refeicao: ref.tipo_refeicao,
    categoria: ref.categoria,
    ficha_tecnica_id: ref.ficha_tecnica_id,
    codigo_prato: ref.codigo_prato,
    nome_prato: ref.nome_prato || ref.ficha_tecnica_nome,
    custo_unitario: ref.custo_porcao,
    custo_total_item: ref.custo_porcao,
    observacoes: ref.observacoes,
    ordem: ref.ordem,
  };
}

function groupFallback(refeicoes: CardapioRefeicao[] = []): CardapioRefeicaoGrupo[] {
  const groups = new Map<string, CardapioComponente[]>();
  for (const ref of refeicoes) {
    const key = ref.tipo_refeicao || "almoco";
    const current = groups.get(key) || [];
    current.push(toComponent(ref));
    groups.set(key, current);
  }
  return Array.from(groups.entries()).map(([tipo, componentes]) => ({
    tipo_refeicao: tipo,
    label: TIPOS_REFEICAO[tipo] || tipo,
    custo_total: componentes.reduce((sum, item) => sum + Number(item.custo_total_item || item.custo_unitario || 0), 0),
    componentes,
  }));
}

export default function CardapioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [cardapio, setCardapio] = useState<Cardapio | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => { loadCardapio(); }, [id]);

  async function loadCardapio() {
    setLoading(true);
    try { setCardapio(await api.cardapios.get(id)); } catch { router.push("/cardapios"); }
    setLoading(false);
  }

  async function handleApproval(status: string, comment?: string) {
    setActionLoading(status);
    try {
      if (status === "publicado") {
        await api.cardapios.publicar(id);
      } else if (status === "em_revisao") {
        await api.cardapios.aprovar(id, "solicitado_revisao", comment);
      } else {
        await api.cardapios.aprovar(id, status, comment);
      }
      setCardapio(await api.cardapios.get(id));
    } catch (e: any) { alert(e.message || "Erro na aprovação"); }
    setActionLoading(null);
  }

  function handlePrint() {
    window.print();
  }

  if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Spinner size={28} /></div>;
  if (!cardapio) return null;

  const dias = cardapio.dias || [];

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <button onClick={() => router.push("/cardapios")} className="mb-2 flex items-center gap-1 text-sm text-link hover:underline">
          <ArrowLeft size={14} /> Voltar
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[28px] font-medium tracking-tight text-ink">{cardapio.nome}</h1>
            <p className="mt-1.5 text-sm text-ink-muted-48">
              {cardapio.periodo_inicio ? formatDate(cardapio.periodo_inicio) : "—"} — {cardapio.periodo_fim ? formatDate(cardapio.periodo_fim) : "—"}
              {cardapio.num_dias ? ` · ${cardapio.num_dias} dias` : ""}
              {cardapio.custo_medio_dia != null ? ` · ${formatCurrency(cardapio.custo_medio_dia)}/dia` : ""}
            </p>
          </div>
          <StatusBadge status={cardapio.status} />
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {cardapio.status === "rascunho" && (
          <Button size="sm" onClick={() => handleApproval("em_revisao")} disabled={!!actionLoading}>
            {actionLoading === "em_revisao" ? <Spinner size={14} /> : <Eye size={14} />} Enviar para Revisão
          </Button>
        )}
        {(cardapio.status === "em_revisao" || cardapio.status === "aguardando_aprovacao") && (
          <Button size="sm" onClick={() => handleApproval("aprovado")} disabled={!!actionLoading}>
            {actionLoading === "aprovado" ? <Spinner size={14} /> : <CheckCircle2 size={14} />} Aprovar
          </Button>
        )}
        {cardapio.status === "aprovado" && (
          <Button size="sm" onClick={() => handleApproval("publicado")} disabled={!!actionLoading}>
            {actionLoading === "publicado" ? <Spinner size={14} /> : <Send size={14} />} Publicar
          </Button>
        )}
        <div className="ml-auto flex flex-wrap gap-2 print:hidden">
          <button onClick={() => api.cardapios.download(id, "xlsx")} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2">
            <Download size={14} /> XLSX
          </button>
          <button onClick={() => api.cardapios.download(id, "csv")} className="inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-soft">
            <FileSpreadsheet size={14} /> CSV
          </button>
          <button onClick={() => api.cardapios.download(id, "pdf")} className="inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-soft">
            <FileText size={14} /> PDF
          </button>
          <button onClick={handlePrint} className="inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-soft">
            <Printer size={14} /> Imprimir
          </button>
        </div>
      </div>

      {dias.length === 0 ? (
        <div className="rounded-lg border border-hairline bg-white p-8 text-center">
          <p className="text-sm text-ink-muted-48">Este cardápio ainda não possui dias detalhados.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {dias.map((dia, di) => (
            <div key={dia.id || di} className="rounded-lg border border-hairline bg-white">
              {(() => {
                const refeicoesAgrupadas = dia.refeicoes_agrupadas?.length
                  ? dia.refeicoes_agrupadas
                  : groupFallback(dia.refeicoes || []);
                return (
                  <>
              <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                <div>
                  <span className="text-[18px] font-medium text-ink">Dia {dia.numero_dia || di + 1}</span>
                  {dia.dia_semana && <span className="ml-2 text-xs text-ink-muted-48">{dia.dia_semana}</span>}
                </div>
                {dia.custo_total != null && <span className="text-sm font-medium text-ink">{formatCurrency(dia.custo_total)}</span>}
              </div>
              {refeicoesAgrupadas.length === 0 ? (
                <p className="px-5 py-4 text-xs text-ink-muted-48">Sem refeições registradas</p>
              ) : (
                <div className="divide-y divide-hairline">
                  {refeicoesAgrupadas.map((grupo, gi) => (
                    <section key={`${grupo.tipo_refeicao}-${gi}`} className="px-5 py-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted-48">Refeição</p>
                          <h3 className="text-base font-medium text-ink">{grupo.label || TIPOS_REFEICAO[grupo.tipo_refeicao] || grupo.tipo_refeicao}</h3>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted-48">Total da refeição</p>
                          <p className="text-sm font-medium text-ink">{formatCurrency(grupo.custo_total || 0)}</p>
                        </div>
                      </div>

                      <div className="overflow-hidden rounded-lg border border-hairline">
                        <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)_9rem_9rem] gap-3 border-b border-hairline bg-surface-soft px-4 py-2 text-[11px] font-medium uppercase tracking-wide text-ink-muted-48">
                          <span>Categoria</span>
                          <span>Item</span>
                          <span className="text-right">Unitário</span>
                          <span className="text-right">Total item</span>
                        </div>
                        {(grupo.componentes || []).map((item, ii) => (
                          <div
                            key={`${grupo.tipo_refeicao}-${ii}-${item.nome_prato || item.codigo_prato || "item"}`}
                            className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)_9rem_9rem] gap-3 border-b border-hairline px-4 py-3 last:border-b-0"
                          >
                            <div className="text-sm text-ink-muted-80">{item.categoria || "Sem categoria"}</div>
                            <div className="text-sm text-ink">{item.nome_prato || "—"}</div>
                            <div className="text-right text-sm text-ink-muted-80">{formatCurrency(item.custo_unitario || 0)}</div>
                            <div className="text-right text-sm font-medium text-ink">{formatCurrency(item.custo_total_item || item.custo_unitario || 0)}</div>
                          </div>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              )}
                  </>
                );
              })()}
            </div>
          ))}
        </div>
      )}

      {cardapio.observacoes && (
        <div className="mt-4 rounded-lg border border-hairline bg-white p-5">
          <h3 className="mb-2 text-lg font-medium text-ink">Observações</h3>
          <p className="text-sm text-ink-muted-80 whitespace-pre-wrap">{cardapio.observacoes}</p>
        </div>
      )}
    </div>
  );
}
