"use client";

import { useState } from "react";
import {
  FileText,
  Settings2,
  ChefHat,
  DollarSign,
  Clock,
  Sparkles,
  CheckCircle2,
  Loader2,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Download,
  FileSpreadsheet,
  FileText as FileTextIcon,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentAvatar, UserAvatar } from "@/components/chat/ChatContainer";
import { AgentMarkdown } from "@/components/chat/AgentMarkdown";
import type { ContratoAnalise } from "@/lib/types";
import type { ConfirmData, ResultData } from "@/components/chat/useChatGenerator";
import api from "@/lib/api";

const STEP_LABELS = [
  "Analisando contrato",
  "Definindo estruturas",
  "Selecionando fichas",
  "Montando cardapio",
  "Calculando custos",
  "Revisando cardapio",
  "Finalizando",
  "Concluido",
];

const STEP_ICONS = [FileText, Settings2, FileSpreadsheet, ChefHat, DollarSign, Clock, Sparkles, CheckCircle2];

export interface MessageBubbleProps {
  role: "agent" | "user";
  type: "text" | "analysis" | "pipeline" | "confirm" | "result" | "error" | "uploading";
  content: string;
  analysis?: ContratoAnalise | null;
  pipelineStep?: number;
  pipelineProgress?: number;
  pensamento?: string;
  confirmData?: ConfirmData;
  hitlData?: {
    resumo: any;
    jobId: string;
  };
  resultData?: ResultData;
  erro?: string;
  onSelectContrato?: (id: string) => void;
  loadingContratos?: boolean;
  contratos?: Array<{ id: string; nome: string }>;
  onSetDias?: (v: number) => void;
  onSetRefeicoes?: (v: string[]) => void;
  onSetCustoAlvo?: (v: string) => void;
  onSkipCost?: () => void;
  onSetRestricoes?: (v: string) => void;
  onSkipRestrictions?: () => void;
  onStartGeneration?: () => void;
  onAdjust?: () => void;
  onNewGeneration?: () => void;
  onConfirmHitl?: (confirm: boolean, ajustes?: string) => void;
}

export function MessageBubble(props: MessageBubbleProps) {
  const { role, type, content } = props;

  // User message — coral bubble, right-aligned
  if (role === "user") {
    return (
      <div className="flex items-start justify-end gap-2 sm:gap-3">
        <UserAvatar />
        <div className="max-w-[min(100%,80%)] rounded-2xl rounded-br-md bg-surface-dark px-4 py-2.5 text-sm leading-relaxed text-white sm:max-w-[80%]">
          {content}
        </div>
      </div>
    );
  }

  // Agent message — left-aligned, flat bubble
  const showTextBubble = type !== "uploading" && type !== "error" && (content.trim() || type !== "pipeline");

  return (
    <div className="flex items-start gap-2 sm:gap-3">
      <AgentAvatar />
      <div className="min-w-0 max-w-full space-y-3 sm:max-w-[85%]">
        {showTextBubble ? (
          <div className="rounded-2xl rounded-tl-md border border-hairline/80 bg-white px-3.5 py-3 text-sm leading-relaxed text-ink shadow-sm shadow-black/[0.02] sm:px-4">
            <AgentMarkdown content={content} />
          </div>
        ) : null}
        {type === "analysis" && <AnalysisCard analysis={props.analysis ?? null} />}
        {type === "uploading" && (
          <div className="flex items-center gap-2 rounded-xl bg-surface-soft p-4">
            <Loader2 size={14} className="animate-spin text-ink" />
            <span className="text-sm text-ink-muted-48">{content}</span>
          </div>
        )}
        {type === "pipeline" && (
          <>
            <PipelineView
              step={props.pipelineStep ?? 0}
              progress={props.pipelineProgress ?? 0}
              pensamento={props.pensamento}
            />
            {props.hitlData && (
              <HitlConfirmCard
                data={props.hitlData}
                onConfirm={(ajustes) => props.onConfirmHitl?.(true, ajustes)}
                onReject={() => props.onConfirmHitl?.(false)}
              />
            )}
          </>
        )}
        {type === "confirm" && (
          <ConfirmCard
            data={props.confirmData}
            onStartGeneration={props.onStartGeneration}
            onAdjust={props.onAdjust}
          />
        )}
        {type === "result" && (
          <ResultCard data={props.resultData} onNewGeneration={props.onNewGeneration} />
        )}
        {type === "error" && <ErrorCard erro={props.erro || content} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Analysis Card — cream callout surface (Airtable cream-callout-card)
// ---------------------------------------------------------------------------

function AnalysisCard({ analysis }: { analysis: ContratoAnalise | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!analysis) {
    return (
      <div className="rounded-xl border border-amber-200/60 bg-amber-50 p-4">
        <div className="flex items-start gap-2.5">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800">Analise pendente</p>
            <p className="mt-0.5 text-xs text-amber-700">
              O agente analisara o contrato durante a geracao.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-signature-cream p-4 space-y-3">
      <div className="flex items-center gap-2">
        <FileText size={14} className="text-ink-muted-80" />
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted-80">Analise do Contrato</p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg bg-white/70 p-2.5">
          <p className="text-[10px] font-medium text-ink-muted-48">Refeicoes/dia</p>
          <p className="mt-0.5 text-lg font-semibold text-ink">
            {analysis.servicos?.num_refeicoes_dia || analysis.necessidades?.num_refeicoes_dia || "—"}
          </p>
        </div>
        <div className="rounded-lg bg-white/70 p-2.5">
          <p className="text-[10px] font-medium text-ink-muted-48">Proibicoes</p>
          {analysis.proibicoes?.length > 0 ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {analysis.proibicoes.slice(0, 3).map((p, i) => (
                <span key={i} className="rounded bg-red-100/60 px-1.5 py-0.5 text-[10px] font-medium text-red-700">{p}</span>
              ))}
              {analysis.proibicoes.length > 3 && (
                <span className="text-[10px] text-ink-muted-48">+{analysis.proibicoes.length - 3}</span>
              )}
            </div>
          ) : (
            <p className="mt-0.5 text-xs text-ink-muted-48">Nenhuma</p>
          )}
        </div>
        <div className="rounded-lg bg-white/70 p-2.5">
          <p className="text-[10px] font-medium text-ink-muted-48">Dietas especiais</p>
          {analysis.dietas_especiais?.length > 0 ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {analysis.dietas_especiais.slice(0, 3).map((d, i) => (
                <span key={i} className="rounded bg-blue-100/60 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">{d}</span>
              ))}
            </div>
          ) : (
            <p className="mt-0.5 text-xs text-ink-muted-48">Nenhuma</p>
          )}
        </div>
      </div>

      {analysis.restricoes_alergenos?.length > 0 && (
        <div className="rounded-lg bg-white/70 p-2.5">
          <p className="text-[10px] font-medium text-ink-muted-48">Alergenos</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {analysis.restricoes_alergenos.map((a, i) => (
              <span key={i} className="rounded bg-orange-100/60 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">{a}</span>
            ))}
          </div>
        </div>
      )}

      {analysis.gramaturas && Object.keys(analysis.gramaturas).length > 0 && (
        <div className="rounded-lg bg-white/70 p-2.5">
          <p className="text-[10px] font-medium text-ink-muted-48">Gramaturas por categoria</p>
          <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1">
            {Object.entries(analysis.gramaturas).slice(0, 6).map(([cat, val]) => (
              <div key={cat} className="text-xs">
                <span className="text-ink-muted-48">{cat}:</span>
                <span className="ml-1 font-medium text-ink">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.necessidades?.observacoes && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-ink-muted-80 hover:text-ink"
        >
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          {expanded ? "Ocultar detalhes" : "Ver detalhes completos"}
        </button>
      )}

      {expanded && analysis.necessidades?.observacoes && (
        <div className="rounded-lg bg-white/70 p-3 text-xs leading-relaxed text-ink whitespace-pre-wrap">
          {analysis.necessidades.observacoes}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pipeline View — surface-soft card
// ---------------------------------------------------------------------------

function PipelineView({
  step,
  progress,
  pensamento,
}: {
  step: number;
  progress: number;
  pensamento?: string;
}) {
  const [showThinking, setShowThinking] = useState(false);

  return (
    <div className="rounded-xl bg-surface-soft p-4 space-y-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted-48">Progresso</p>

      {/* Progress bar at top */}
      {progress > 0 && progress < 100 && (
        <div>
          <div className="h-1.5 rounded-full bg-ink/8">
            <div
              className="h-1.5 rounded-full bg-ink transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1 text-right text-[10px] text-ink-muted-48">{progress}%</p>
        </div>
      )}

      <div className="relative">
        {/* Vertical connecting line */}
        <div className="absolute left-3 top-3 bottom-3 w-px bg-ink/8" />

        <div className="relative space-y-3">
          {STEP_LABELS.map((label, i) => {
            const Icon = STEP_ICONS[i];
            const isDone = step > i;
            const isCurrent = step === i;
            return (
              <div key={i} className="flex items-center gap-3">
                <div
                  className={cn(
                    "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all",
                    isDone
                      ? "border-success bg-success text-white"
                      : isCurrent
                      ? "border-ink bg-ink/10 text-ink ring-2 ring-ink/15"
                      : "border-ink/10 bg-surface-soft text-ink-muted-48"
                  )}
                >
                  {isDone ? (
                    <CheckCircle2 size={12} />
                  ) : isCurrent ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <Icon size={12} />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs transition-colors",
                    isDone
                      ? "font-medium text-success"
                      : isCurrent
                      ? "font-medium text-ink"
                      : "text-ink-muted-48"
                  )}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {pensamento && (
        <div>
          <button
            onClick={() => setShowThinking(!showThinking)}
            className="flex items-center gap-1.5 text-xs text-ink-muted-48 hover:text-ink"
          >
            <ChefHat size={12} className="text-ink" />
            Pensamento
            {showThinking ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </button>
          {showThinking && (
            <div className="mt-1.5 max-h-32 overflow-y-auto rounded-md bg-white/60 p-2.5 text-[11px] leading-relaxed text-ink-muted-48 whitespace-pre-wrap">
              {pensamento}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Confirm Card — dark signature surface (Airtable hero-card-dark)
// ---------------------------------------------------------------------------

function ConfirmCard({
  data,
  onStartGeneration,
  onAdjust,
}: {
  data?: ConfirmData;
  onStartGeneration?: () => void;
  onAdjust?: () => void;
}) {
  if (!data) return null;

  const mealLabels: Record<string, string> = {
    cafe_manha: "Cafe da Manha",
    almoco: "Almoco",
    lanche_tarde: "Lanche da Tarde",
    jantar: "Jantar",
    lanche_manha: "Lanche da Manha",
    ceia: "Ceia",
  };

  return (
    <div className="rounded-xl bg-surface-dark p-5 text-white space-y-4 shadow-sm">
      <div className="flex items-center gap-2">
        <ChefHat size={16} className="text-ink" />
        <p className="text-xs font-semibold uppercase tracking-wide text-white/60">Resumo da Geracao</p>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-white/10 p-3">
          <span className="text-white/50">Contrato:</span>
          <p className="mt-0.5 font-semibold text-white">{data.contratoNome || "Nenhum"}</p>
        </div>
        <div className="rounded-lg bg-white/10 p-3">
          <span className="text-white/50">Dias:</span>
          <p className="mt-0.5 font-semibold text-white">{data.dias}</p>
        </div>
        <div className="rounded-lg bg-white/10 p-3">
          <span className="text-white/50">Refeicoes:</span>
          <p className="mt-0.5 font-medium text-white">
            {data.refeicoes.map((r) => mealLabels[r] || r).join(", ")}
          </p>
        </div>
        <div className="rounded-lg bg-white/10 p-3">
          <span className="text-white/50">Custo alvo:</span>
          <p className="mt-0.5 font-medium text-white">
            {data.custoAlvo ? `R$ ${data.custoAlvo}/dia` : "Nao definido"}
          </p>
        </div>
        {data.modeloLabel && (
          <div className="rounded-lg bg-white/10 p-3">
            <span className="text-white/50">Modelo IA:</span>
            <p className="mt-0.5 font-medium text-white">{data.modeloLabel}</p>
          </div>
        )}
      </div>

      {data.restricoes && (
        <div className="rounded-lg bg-white/10 p-3">
          <span className="text-white/50">Restricoes:</span>
          <p className="mt-0.5 font-medium text-white">{data.restricoes}</p>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={onStartGeneration}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2"
        >
          <Sparkles size={16} />
          Gerar Cardapio
        </button>
        <button
          onClick={onAdjust}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-white/20 bg-white/10 px-4 py-3 text-sm font-medium text-white hover:bg-white/20 transition-colors"
        >
          Ajustar
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result Card — cream callout for success
// ---------------------------------------------------------------------------

function ResultCard({
  data,
  onNewGeneration,
}: {
  data?: ResultData;
  onNewGeneration?: () => void;
}) {
  if (!data) return null;

  const handleDownload = (formato: string) => {
    if (data.cardapioId) {
      api.cardapios.download(data.cardapioId, formato);
    }
  };

  return (
    <div className="rounded-xl bg-signature-cream p-5 space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/15">
          <CheckCircle2 size={18} className="text-success" />
        </div>
        <div>
          <p className="text-sm font-bold text-ink">{data.nome}</p>
          <p className="text-xs text-ink-muted-48">
            {data.numDias} dias
            {data.custoMedioDia > 0 && ` • Custo medio: R$ ${data.custoMedioDia.toFixed(2)}/dia`}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <a
          href={api.gerar.download(data.jobId, "xlsx")}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2"
        >
          <Download size={12} /> XLSX
        </a>
        <button
          onClick={() => handleDownload("csv")}
          className="flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-4 py-2 text-xs font-medium text-ink hover:bg-surface-soft hover:shadow-sm transition-all"
        >
          <FileSpreadsheet size={12} /> CSV
        </button>
        <button
          onClick={() => handleDownload("pdf")}
          className="flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-4 py-2 text-xs font-medium text-ink hover:bg-surface-soft hover:shadow-sm transition-all"
        >
          <FileTextIcon size={12} /> PDF
        </button>
        <button
          onClick={() => handleDownload("txt")}
          className="flex items-center gap-1.5 rounded-lg border border-hairline bg-white px-4 py-2 text-xs font-medium text-ink hover:bg-surface-soft hover:shadow-sm transition-all"
        >
          <FileText size={12} /> TXT
        </button>
        {data.cardapioId && (
          <a
            href={`/cardapios/${data.cardapioId}`}
            className="flex items-center gap-1.5 rounded-lg border border-hairline px-4 py-2 text-xs font-medium text-ink transition-colors hover:bg-surface-soft"
          >
            Ver Cardapio
          </a>
        )}
      </div>

      <button
        onClick={onNewGeneration}
        className="text-xs text-link hover:underline"
      >
        Gerar outro cardapio
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error Card
// ---------------------------------------------------------------------------

function ErrorCard({ erro }: { erro: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-2.5">
        <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-600" />
        <p className="text-sm text-red-700">{erro}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HITL Confirm Card
// ---------------------------------------------------------------------------

function HitlConfirmCard({
  data,
  onConfirm,
  onReject,
}: {
  data: { resumo: any; jobId: string };
  onConfirm: (ajustes?: string) => void;
  onReject: () => void;
}) {
  const [ajustes, setAjustes] = useState("");

  return (
    <div className="rounded-xl border border-amber-200/60 bg-amber-50 p-5 space-y-4 mt-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
          <AlertCircle size={18} className="text-amber-600" />
        </div>
        <div>
          <p className="text-sm font-bold text-amber-900">Analise do Contrato Concluida</p>
          <p className="text-xs text-amber-800/80 mt-1">
            Por favor, verifique as regras extraidas do contrato antes de prosseguirmos com a geracao do cardapio.
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-white/60 p-3 text-xs leading-relaxed text-ink/80 whitespace-pre-wrap max-h-48 overflow-y-auto border border-amber-200/40">
        {typeof data.resumo === "string"
          ? data.resumo
          : data.resumo.texto || JSON.stringify(data.resumo, null, 2)}
      </div>

      <div className="space-y-2">
        <label className="text-xs font-medium text-amber-900 block">
          Ajustes adicionais (Opcional):
        </label>
        <textarea
          className="w-full rounded-lg border border-amber-200/60 bg-white p-3 text-sm text-ink placeholder-ink-muted-48 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400 resize-none"
          rows={2}
          placeholder="Ex: Nao esqueca de variar as proteinas..."
          value={ajustes}
          onChange={(e) => setAjustes(e.target.value)}
        />
      </div>

      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onConfirm(ajustes)}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2"
        >
          <CheckCircle2 size={16} />
          Confirmar e Continuar
        </button>
        <button
          onClick={onReject}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-amber-200 bg-white px-4 py-3 text-sm font-medium text-amber-800 hover:bg-amber-100 transition-colors"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
