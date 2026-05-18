"use client";
import { Settings2 } from "lucide-react";
import { API_RUNTIME_TARGET, RUNTIME_ENV } from "@/lib/api";

type LlmModel = {
  id: string;
  label?: string;
  provider?: string;
};

type GerarTopBarProps = {
  llmModel: string;
  generationModels?: LlmModel[];
  reviewLlmModel?: string;
  reviewModels?: LlmModel[];
  loadingModels: boolean;
  onChangeModel: (modelId: string) => void;
  onChangeReviewModel?: (modelId: string) => void;
};

export function GerarTopBar({
  llmModel,
  generationModels = [],
  reviewLlmModel = "",
  reviewModels = [],
  loadingModels,
  onChangeModel,
  onChangeReviewModel = () => {},
}: GerarTopBarProps) {
  const hasGenerationModels = generationModels.length > 0;
  const hasReviewModels = reviewModels.length > 0;
  const generatorValue = hasGenerationModels ? llmModel || generationModels[0].id : "";
  const reviewerValue = hasReviewModels ? reviewLlmModel || reviewModels[0].id : "";
  const runtimeLabel = RUNTIME_ENV === "production" ? "production" : RUNTIME_ENV === "staging" ? "staging" : "local";

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <span
        title={`API alvo: ${API_RUNTIME_TARGET}`}
        className="inline-flex items-center rounded-full border border-hairline bg-surface-soft px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-ink-muted-48"
      >
        {runtimeLabel}
      </span>
      <label className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-white px-2 py-1.5 text-sm text-zinc-700">
        <Settings2 size={14} className="text-ink-muted-48" />
        <span className="text-xs font-medium text-ink-muted-48">Gerador</span>
        <select
          value={generatorValue}
          onChange={(event) => onChangeModel(event.target.value)}
          disabled={loadingModels || !hasGenerationModels}
          className="h-7 min-w-[220px] border-0 bg-transparent px-1 py-1 text-sm text-zinc-900 focus:outline-none"
        >
          {hasGenerationModels ? generationModels.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label ?? model.id}
              {model.provider ? ` (${model.provider})` : ""}
            </option>
          )) : (
            <option value="">
              {loadingModels ? "Carregando modelos..." : "Modelos indisponíveis"}
            </option>
          )}
        </select>
      </label>
      <label className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-white px-2 py-1.5 text-sm text-zinc-700">
        <span className="text-xs font-medium text-ink-muted-48">Revisor</span>
        <select
          value={reviewerValue}
          onChange={(event) => onChangeReviewModel(event.target.value)}
          disabled={loadingModels || !hasReviewModels}
          className="h-7 min-w-[220px] border-0 bg-transparent px-1 py-1 text-sm text-zinc-900 focus:outline-none"
        >
          {hasReviewModels ? reviewModels.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label ?? model.id}
              {model.provider ? ` (${model.provider})` : ""}
            </option>
          )) : (
            <option value="">
              {loadingModels ? "Carregando revisores..." : "Revisores indisponíveis"}
            </option>
          )}
        </select>
      </label>
    </div>
  );
}
