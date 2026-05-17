"use client";

import {
  CheckCircle2,
  ChefHat,
  Clock,
  DollarSign,
  FileSpreadsheet,
  FileText,
  Loader2,
  Settings2,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const GERAR_PIPELINE_STEP_LABELS = [
  "Analisando contrato",
  "Definindo estruturas",
  "Selecionando fichas",
  "Montando cardapio",
  "Calculando custos",
  "Revisando cardapio",
  "Finalizando",
  "Concluido",
] as const;

const STEP_ICONS = [FileText, Settings2, FileSpreadsheet, ChefHat, DollarSign, Clock, Sparkles, CheckCircle2];

interface GerarProgressRailProps {
  step: number;
  progress: number;
  className?: string;
}

export function GerarProgressRail({ step, progress, className }: GerarProgressRailProps) {
  const safeStep = Math.max(0, Math.min(GERAR_PIPELINE_STEP_LABELS.length - 1, step));
  const safeProgress = Math.max(0, Math.min(100, Math.round(progress)));
  const currentLabel = GERAR_PIPELINE_STEP_LABELS[safeStep];
  const CurrentIcon = STEP_ICONS[safeStep];

  return (
    <div className={cn("rounded-xl border border-hairline/80 bg-white/70 p-3", className)}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex items-center gap-2">
          <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink/8 text-ink">
            {safeProgress >= 100 ? (
              <CheckCircle2 size={12} />
            ) : safeStep === GERAR_PIPELINE_STEP_LABELS.length - 1 ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <CurrentIcon size={12} />
            )}
          </div>
          <p className="truncate text-xs font-medium text-ink">{currentLabel}</p>
        </div>
        <span className="shrink-0 text-[11px] font-semibold text-ink-muted-80">{safeProgress}%</span>
      </div>

      <div className="mt-2 h-1.5 rounded-full bg-ink/8">
        <div
          className="h-1.5 rounded-full bg-ink transition-all duration-500"
          style={{ width: `${safeProgress}%` }}
        />
      </div>

      <div className="mt-2 flex items-center gap-1.5" aria-hidden>
        {GERAR_PIPELINE_STEP_LABELS.map((label, index) => {
          const isDone = safeStep > index || (safeProgress >= 100 && safeStep === index);
          const isCurrent = safeStep === index && safeProgress < 100;
          return (
            <div
              key={label}
              className={cn(
                "h-1.5 flex-1 rounded-full transition-colors",
                isDone ? "bg-success" : isCurrent ? "bg-ink/50" : "bg-ink/10"
              )}
            />
          );
        })}
      </div>
    </div>
  );
}
