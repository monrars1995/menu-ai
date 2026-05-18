"use client";
import { Settings2 } from "lucide-react";

type LlmModel = {
  id: string;
  label?: string;
  provider?: string;
};

type GerarTopBarProps = {
  llmModel: string;
  llmModels: LlmModel[];
  loadingModels: boolean;
  onChangeModel: (modelId: string) => void;
};

export function GerarTopBar({
  llmModel,
  llmModels,
  loadingModels,
  onChangeModel,
}: GerarTopBarProps) {
  const hasModels = llmModels.length > 0;
  const safeValue = hasModels ? llmModel || llmModels[0].id : "";

  return (
    <div className="flex items-center justify-end">
      <label className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-white px-2 py-1.5 text-sm text-zinc-700">
        <Settings2 size={14} className="text-ink-muted-48" />
        <select
          value={safeValue}
          onChange={(event) => onChangeModel(event.target.value)}
          disabled={loadingModels || !hasModels}
          className="h-7 min-w-[220px] border-0 bg-transparent px-1 py-1 text-sm text-zinc-900 focus:outline-none"
        >
          {hasModels ? llmModels.map((model) => (
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
    </div>
  );
}
