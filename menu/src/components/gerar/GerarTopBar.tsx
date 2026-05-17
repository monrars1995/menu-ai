"use client";

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
    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-sm font-medium text-zinc-900">Base operacional</p>
      </div>
      <label className="inline-flex items-center gap-2 text-sm text-zinc-700">
        <span>Modelo IA</span>
        <select
          value={safeValue}
          onChange={(event) => onChangeModel(event.target.value)}
          disabled={loadingModels || !hasModels}
          className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900"
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
