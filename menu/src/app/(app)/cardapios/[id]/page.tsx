"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import type { Cardapio } from "@/lib/types";
import { formatCurrency, formatDate, statusBadge } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Spinner } from "@/components/ui/loading";
import { ArrowLeft, Download, FileText, CheckCircle2, Send, Eye, Printer, FileSpreadsheet } from "lucide-react";

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
      await api.cardapios.aprovar(id, status, comment);
      setCardapio(await api.cardapios.get(id));
    } catch (e: any) { alert(e.message || "Erro na aprovação"); }
    setActionLoading(null);
  }

  function handlePrint() {
    window.print();
  }

  if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Spinner size={28} /></div>;
  if (!cardapio) return null;

  const badge = statusBadge(cardapio.status);

  const dias = cardapio.dias || [];
  const TIPOS_REFEICAO: Record<string, string> = {
    cafe_manha: "Café da Manhã", lanche_manha: "Lanche da Manhã", almoco: "Almoço",
    lanche_tarde: "Lanche da Tarde", jantar: "Jantar", ceia: "Ceia",
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <button onClick={() => router.push("/cardapios")} className="mb-2 flex items-center gap-1 text-sm text-link hover:underline">
          <ArrowLeft size={14} /> Voltar
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[28px] font-display text-ink">{cardapio.nome}</h1>
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
          <button onClick={() => api.cardapios.download(id, "xlsx")} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-active">
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
              <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                <div>
                  <span className="font-display text-[18px] text-ink">Dia {dia.numero_dia || di + 1}</span>
                  {dia.dia_semana && <span className="ml-2 text-xs text-ink-muted-48">{dia.dia_semana}</span>}
                </div>
                {dia.custo_total != null && <span className="text-sm font-medium text-ink">{formatCurrency(dia.custo_total)}</span>}
              </div>
              {(dia.refeicoes || []).length === 0 ? (
                <p className="px-5 py-4 text-xs text-ink-muted-48">Sem refeições registradas</p>
              ) : (
                <div className="divide-y divide-hairline">
                  {(dia.refeicoes || []).map((ref, ri) => (
                    <div key={ri} className="flex items-center justify-between px-5 py-3">
                      <div>
                        <span className="text-xs font-medium uppercase tracking-wide text-primary">
                          {TIPOS_REFEICAO[ref.tipo_refeicao] || ref.tipo_refeicao}
                        </span>
                        <p className="mt-0.5 text-sm text-ink">{ref.nome_prato || ref.ficha_tecnica_nome || "—"}</p>
                      </div>
                      {ref.custo_porcao != null && <span className="text-sm text-ink-muted-48">{formatCurrency(ref.custo_porcao)}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {cardapio.observacoes && (
        <div className="mt-4 rounded-lg border border-hairline bg-white p-5">
          <h3 className="mb-2 font-display text-[18px] text-ink">Observações</h3>
          <p className="text-sm text-ink-muted-80 whitespace-pre-wrap">{cardapio.observacoes}</p>
        </div>
      )}
    </div>
  );
}
