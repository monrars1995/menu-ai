"use client";

import {
  ChatContainer,
  MessageBubble,
  MessageInput,
  useChatGenerator,
} from "@/components/chat";
import { ContractUpload } from "@/components/wizard/ContractUpload";
import { Cpu } from "lucide-react";

function LlmModelSelect({
  value,
  models,
  loading,
  onChange,
}: {
  value: string;
  models: Array<{ id: string; label?: string; provider?: string; description?: string }>;
  loading: boolean;
  onChange: (modelId: string) => void;
}) {
  if (loading) {
    return (
      <div className="inline-flex h-10 items-center gap-2 rounded-md border border-hairline bg-white px-3 text-xs text-ink-muted-48">
        <Cpu size={14} />
        Carregando modelos...
      </div>
    );
  }
  if (!models.length) {
    return (
      <div className="inline-flex h-10 items-center gap-2 rounded-md border border-red-200 bg-white px-3 text-xs text-red-700">
        <Cpu size={14} />
        Modelos indisponiveis
      </div>
    );
  }

  const selected = models.find((m) => m.id === value);

  return (
    <label className="flex min-w-0 items-center gap-2 rounded-md border border-hairline bg-white px-3 py-2 text-xs text-ink-muted-48">
      <Cpu size={14} className="shrink-0" />
      <span className="hidden shrink-0 sm:inline">Modelo IA</span>
      <select
        value={value || models[0].id}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-0 bg-transparent text-sm font-medium text-ink outline-none"
        title={selected?.description || selected?.id}
      >
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label || model.id} {model.provider ? `(${model.provider})` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function GerarPage() {
  const {
    state,
    selectContrato,
    goToUpload,
    handleInlineUpload,
    setDias,
    setRefeicoes,
    setCustoAlvo,
    setRestricoes,
    handleSkipCost,
    handleSkipRestrictions,
    handleAdjust,
    startGeneration,
    handleNewGeneration,
    confirmHitl,
    sendChatMessage,
    setLlmModel,
  } = useChatGenerator();

  const isWizardStart = state.phase === "welcome" || state.phase === "uploading";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex items-center justify-end">
        <LlmModelSelect
          value={state.llmModel}
          models={state.llmModels}
          loading={state.loadingLlmModels}
          onChange={setLlmModel}
        />
      </div>

      {isWizardStart ? (
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-5xl space-y-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-ink">Novo Cardápio</h1>
              <p className="mt-2 text-ink-muted">
                Comece selecionando um contrato existente ou faça upload de um novo PDF para análise.
              </p>
            </div>
            <ContractUpload
              onSelect={selectContrato}
              onUpload={handleInlineUpload}
            />
          </div>
        </div>
      ) : (
        <ChatContainer className="min-h-0 flex-1" onFileDrop={handleInlineUpload}>
          {state.messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              type={msg.type}
              content={msg.content}
              analysis={msg.analysis}
              pipelineStep={msg.pipelineStep}
              pipelineProgress={msg.pipelineProgress}
              pensamento={msg.pensamento}
              confirmData={msg.confirmData}
              resultData={msg.resultData}
              erro={msg.erro}
              onSelectContrato={selectContrato}
              loadingContratos={state.loadingContratos}
              contratos={state.contratos}
              onStartGeneration={startGeneration}
              onAdjust={handleAdjust}
              onNewGeneration={handleNewGeneration}
              onConfirmHitl={confirmHitl}
            />
          ))}
        </ChatContainer>
      )}

      {/* Input area */}
      {!isWizardStart && (
        <MessageInput
          phase={state.phase}
          contratos={state.contratos}
          loadingContratos={state.loadingContratos}
          onSelectContrato={selectContrato}
          onGoToUpload={goToUpload}
          onInlineUpload={handleInlineUpload}
          diasValue={state.dias}
          onSetDias={setDias}
          refeicoesValue={state.refeicoes}
          onSetRefeicoes={setRefeicoes}
          custoValue={state.custoAlvo}
          onSetCustoAlvo={setCustoAlvo}
          onSkipCost={handleSkipCost}
          restricoesValue={state.restricoes}
          onSetRestricoes={setRestricoes}
          onSkipRestrictions={handleSkipRestrictions}
          onSendMessage={sendChatMessage}
        />
      )}
    </div>
  );
}
