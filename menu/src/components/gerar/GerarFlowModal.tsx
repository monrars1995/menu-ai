"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, FileText, Loader2, Sparkles } from "lucide-react";
import type { ContratoAnalise } from "@/lib/types";
import type { ChatPhase, ConfirmData } from "@/components/chat";
import { MealSelector } from "@/components/meal-selector";
import { ContractUpload } from "@/components/wizard/ContractUpload";
import { cn } from "@/lib/utils";

type GerarFlowModalProps = {
  phase: ChatPhase;
  open: boolean;
  loading?: boolean;
  contratoNome?: string;
  contratoAnalise?: ContratoAnalise | null;
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  confirmData: ConfirmData | null;
  onAnalyzeContrato: () => void;
  onSelectContrato: (contratoId: string) => void;
  onUploadContrato: (file: File) => void;
  onSetDias: (value: number) => void;
  onSetRefeicoes: (value: string[]) => void;
  onSetCustoAlvo: (value: string) => void;
  onSkipCost: () => void;
  onSetRestricoes: (value: string) => void;
  onSkipRestrictions: () => void;
  onStartGeneration: () => void;
  onAdjust: () => void;
};

const overlayPhases: ChatPhase[] = [
  "welcome",
  "analysis",
  "upload-confirm",
  "config-days",
  "config-meals",
  "config-cost",
  "config-restrictions",
  "confirm",
];

function formatMealLabel(value: string): string {
  const map: Record<string, string> = {
    cafe_manha: "Café da manhã",
    almoco: "Almoço",
    lanche_tarde: "Lanche da tarde",
    jantar: "Jantar",
    lanche_manha: "Lanche da manhã",
    ceia: "Ceia",
  };
  return map[value] || value;
}

function normalizeContractRules(analise: ContratoAnalise | null | undefined): string[] {
  if (!analise) return [];
  const linhas: string[] = [];
  if (analise.dietas_especiais?.length) {
    linhas.push(`Dietas especiais: ${analise.dietas_especiais.join(", ")}`);
  }
  if (analise.proibicoes?.length) {
    linhas.push(`Proibições: ${analise.proibicoes.join(", ")}`);
  }
  if (analise.restricoes_alergenos?.length) {
    linhas.push(`Alergênicos: ${analise.restricoes_alergenos.join(", ")}`);
  }
  const incidencias = analise.incidencias;
  if (Array.isArray(incidencias) && incidencias.length) {
    linhas.push(`Incidências obrigatórias: ${incidencias.join(", ")}`);
  } else if (incidencias && typeof incidencias === "object") {
    const items = Object.entries(incidencias)
      .map(([k, v]) => `${k}: ${String(v)}`)
      .filter(Boolean);
    if (items.length) linhas.push(`Incidências obrigatórias: ${items.join(", ")}`);
  }
  return linhas;
}

export function GerarFlowModal({
  phase,
  open,
  loading,
  contratoNome,
  contratoAnalise,
  dias,
  refeicoes,
  custoAlvo,
  restricoes,
  confirmData,
  onAnalyzeContrato,
  onSelectContrato,
  onUploadContrato,
  onSetDias,
  onSetRefeicoes,
  onSetCustoAlvo,
  onSkipCost,
  onSetRestricoes,
  onSkipRestrictions,
  onStartGeneration,
  onAdjust,
}: GerarFlowModalProps) {
  const [diasDraft, setDiasDraft] = useState(String(dias || 5));
  const [refeicoesDraft, setRefeicoesDraft] = useState<string[]>(refeicoes || []);
  const [extraRefeicoes, setExtraRefeicoes] = useState("");
  const [custoDraft, setCustoDraft] = useState(custoAlvo || "");
  const [restricoesDraft, setRestricoesDraft] = useState(restricoes || "");

  useEffect(() => {
    if (!open) return;
    if (phase === "config-days") setDiasDraft(String(dias || 5));
    if (phase === "config-meals") {
      setRefeicoesDraft(refeicoes || []);
      setExtraRefeicoes("");
    }
    if (phase === "config-cost") setCustoDraft(custoAlvo || "");
    if (phase === "config-restrictions") setRestricoesDraft(restricoes || "");
  }, [open, phase, dias, refeicoes, custoAlvo, restricoes]);

  const visible = open && overlayPhases.includes(phase);
  const contractRules = useMemo(
    () => normalizeContractRules(contratoAnalise),
    [contratoAnalise]
  );

  if (!visible) return null;

  function confirmMeals() {
    const extras = extraRefeicoes
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const merged = Array.from(new Set([...refeicoesDraft, ...extras]));
    if (merged.length) onSetRefeicoes(merged);
  }

  return (
    <div className="pointer-events-none absolute inset-0 z-20 flex items-end justify-center p-4 pb-6 sm:items-center">
      <div className="pointer-events-auto w-full max-w-2xl rounded-xl border border-hairline bg-white/95 shadow-2xl backdrop-blur-sm">
        {phase === "analysis" ? (
          <div className="p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface-soft">
              <Loader2 className="h-5 w-5 animate-spin text-ink" />
            </div>
            <h3 className="text-base font-semibold text-ink">Analisando contrato</h3>
            <p className="mt-1 text-sm text-ink-muted-48">
              Extraindo regras e estrutura para iniciar a geração.
            </p>
          </div>
        ) : null}

        {phase === "welcome" ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Iniciar geração</h3>
            <p className="mt-1 text-sm text-ink-muted-48">
              Envie um contrato ou selecione um contrato salvo.
            </p>
            <div className="mt-4">
              <ContractUpload onSelect={onSelectContrato} onUpload={onUploadContrato} />
            </div>
          </div>
        ) : null}

        {phase === "upload-confirm" ? (
          <div className="p-6">
            <div className="rounded-xl border border-hairline bg-surface-soft p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                  <CheckCircle2 size={16} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-ink">Upload concluído</h3>
                  <p className="mt-1 text-sm text-ink-muted-48">Contrato pronto para análise.</p>
                  <p className="mt-2 flex items-center gap-1.5 truncate text-sm font-medium text-ink" title={contratoNome || "Sem nome"}>
                    <FileText size={14} className="shrink-0 text-ink-muted-48" />
                    {contratoNome || "Sem nome"}
                  </p>
                </div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={onAnalyzeContrato}
                disabled={Boolean(loading)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white",
                  "transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border",
                  loading && "cursor-not-allowed opacity-60"
                )}
              >
                <Sparkles size={14} />
                Analisar contrato
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        ) : null}

        {phase === "config-days" ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Período do cardápio</h3>
            <p className="mt-1 text-sm text-ink-muted-48">Defina a quantidade de dias.</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                type="number"
                min={1}
                max={30}
                value={diasDraft}
                onChange={(event) => setDiasDraft(event.target.value)}
                className="w-28 rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
              <span className="text-xs text-ink-muted-48">1 a 30 dias</span>
              <button
                type="button"
                onClick={() => {
                  const parsed = parseInt(diasDraft || "5", 10) || 5;
                  onSetDias(Math.max(1, Math.min(30, parsed)));
                }}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active sm:ml-auto"
              >
                Confirmar
              </button>
            </div>
          </div>
        ) : null}

        {phase === "config-meals" ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Refeições</h3>
            <p className="mt-1 text-sm text-ink-muted-48">Selecione as refeições que devem entrar no plano.</p>
            <div className="mt-4">
              <MealSelector selected={refeicoesDraft} onChange={setRefeicoesDraft} />
            </div>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                type="text"
                value={extraRefeicoes}
                onChange={(event) => setExtraRefeicoes(event.target.value)}
                placeholder="Outras refeições (separadas por vírgula)"
                className="w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
              <button
                type="button"
                onClick={confirmMeals}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active"
              >
                Confirmar
              </button>
            </div>
          </div>
        ) : null}

        {phase === "config-cost" ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Custo alvo diário</h3>
            <p className="mt-1 text-sm text-ink-muted-48">Opcional. Se vazio, o sistema otimiza sem teto fixo.</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <span className="text-sm text-ink-muted-48">R$</span>
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  value={custoDraft}
                  onChange={(event) => setCustoDraft(event.target.value)}
                  placeholder="Opcional"
                  className="w-32 rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
                />
              </div>
              <div className="flex items-center gap-2 sm:ml-auto">
                <button
                  type="button"
                  onClick={() => {
                    if (custoDraft.trim()) onSetCustoAlvo(custoDraft.trim());
                    else onSkipCost();
                  }}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active"
                >
                  Confirmar
                </button>
                <button
                  type="button"
                  onClick={onSkipCost}
                  className="rounded-md px-2 py-2 text-sm text-link hover:underline"
                >
                  Pular
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {phase === "config-restrictions" ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Restrições adicionais</h3>
            <p className="mt-1 text-sm text-ink-muted-48">
              Regras do contrato já serão aplicadas automaticamente.
            </p>
            {contractRules.length ? (
              <div className="mt-3 rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-ink-muted-48">Regras fixas do contrato</p>
                <ul className="mt-2 space-y-1 text-sm text-ink">
                  {contractRules.map((rule) => (
                    <li key={rule}>{rule}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="mt-3">
              <textarea
                rows={3}
                value={restricoesDraft}
                onChange={(event) => setRestricoesDraft(event.target.value)}
                placeholder="Ex: sem lactose, sem glúten, baixo sódio..."
                className="w-full resize-none rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
            </div>
            <div className="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  if (restricoesDraft.trim()) onSetRestricoes(restricoesDraft.trim());
                  else onSkipRestrictions();
                }}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active"
              >
                Confirmar
              </button>
              <button
                type="button"
                onClick={onSkipRestrictions}
                className="rounded-md px-2 py-2 text-sm text-link hover:underline"
              >
                Pular
              </button>
            </div>
          </div>
        ) : null}

        {phase === "confirm" && confirmData ? (
          <div className="p-6">
            <h3 className="text-base font-semibold text-ink">Confirmar geração</h3>
            <p className="mt-1 text-sm text-ink-muted-48">Revise os parâmetros antes de iniciar.</p>

            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="text-xs text-ink-muted-48">Contrato</p>
                <p className="mt-1 text-sm font-medium text-ink">{confirmData.contratoNome}</p>
              </div>
              <div className="rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="text-xs text-ink-muted-48">Dias</p>
                <p className="mt-1 text-sm font-medium text-ink">{confirmData.dias}</p>
              </div>
              <div className="rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="text-xs text-ink-muted-48">Refeições</p>
                <p className="mt-1 text-sm font-medium text-ink">
                  {confirmData.refeicoes.map(formatMealLabel).join(", ")}
                </p>
              </div>
              <div className="rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="text-xs text-ink-muted-48">Custo alvo</p>
                <p className="mt-1 text-sm font-medium text-ink">
                  {confirmData.custoAlvo ? `R$ ${confirmData.custoAlvo}/dia` : "Sem alvo"}
                </p>
              </div>
            </div>

            <div className="mt-2 rounded-lg border border-hairline bg-surface-soft p-3">
              <p className="text-xs text-ink-muted-48">Modelo</p>
              <p className="mt-1 text-sm font-medium text-ink">{confirmData.modeloLabel || "Padrão"}</p>
            </div>

            <div className="mt-2 rounded-lg border border-hairline bg-surface-soft p-3">
              <p className="text-xs text-ink-muted-48">Regras fixas do contrato</p>
              <p className="mt-1 whitespace-pre-line text-sm text-ink">
                {confirmData.restricoesContrato || "Nenhuma regra fixa detectada."}
              </p>
            </div>

            <div className="mt-2 rounded-lg border border-hairline bg-surface-soft p-3">
              <p className="text-xs text-ink-muted-48">Restrições adicionais</p>
              <p className="mt-1 whitespace-pre-line text-sm text-ink">
                {confirmData.restricoesAdicionais || "Nenhuma"}
              </p>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={onAdjust}
                className="rounded-lg border border-hairline bg-white px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-surface-soft"
              >
                Ajustar
              </button>
              <button
                type="button"
                onClick={onStartGeneration}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active"
              >
                <Sparkles size={14} />
                Gerar cardápio
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
