"use client";

import {
  ChatContainer,
  MessageBubble,
  MessageInput,
  useChatGenerator,
} from "@/components/chat";
import { ContractUpload } from "@/components/wizard/ContractUpload";

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
  } = useChatGenerator();

  const isWizardStart = state.phase === "welcome" || state.phase === "uploading";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
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
