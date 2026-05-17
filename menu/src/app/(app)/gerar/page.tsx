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
        Modelos indisponíveis
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
    analyzeContrato,
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
    regenerateCardapio,
    approveGeneratedCardapio,
    confirmHitl,
    sendChatMessage,
    setLlmModel,
  } = useChatGenerator();

  const isWizardStart = state.phase === "welcome";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-5 flex items-center justify-end">
        <LlmModelSelect
          value={state.llmModel}
          models={state.llmModels}
          loading={state.loadingLlmModels}
          onChange={setLlmModel}
        />
      </div>

      {isWizardStart ? (
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-[calc(100vh-11rem)] max-w-4xl flex-col items-center justify-center px-3 py-10 sm:px-6">
            <div className="mb-8 text-center">
              <h1 className="text-3xl font-medium tracking-tight text-ink sm:text-4xl">Por onde começamos?</h1>
              <p className="mt-3 text-sm text-ink-muted">
                Envie um contrato ou escolha um contrato salvo para iniciar a análise.
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
              uploadData={msg.uploadData}
              uploadProgress={msg.uploadProgress}
              erro={msg.erro}
              onSelectContrato={selectContrato}
              loadingContratos={state.loadingContratos}
              contratos={state.contratos}
              onStartGeneration={startGeneration}
              onAdjust={handleAdjust}
              onNewGeneration={handleNewGeneration}
              onRegenerate={regenerateCardapio}
              onApproveResult={approveGeneratedCardapio}
              onConfirmHitl={confirmHitl}
              onAnalyzeContrato={analyzeContrato}
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
