"use client";

import {
  ChatContainer,
  MessageBubble,
  MessageInput,
  useChatGenerator,
} from "@/components/chat";
import { GerarEmptyState } from "@/components/gerar/GerarEmptyState";
import { GerarTopBar } from "@/components/gerar/GerarTopBar";
import { GerarWorkspace } from "@/components/gerar/GerarWorkspace";

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
    <GerarWorkspace
      topBar={(
        <GerarTopBar
          llmModel={state.llmModel}
          llmModels={state.llmModels}
          loadingModels={state.loadingLlmModels}
          onChangeModel={setLlmModel}
        />
      )}
      input={isWizardStart ? undefined : (
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
    >
      {isWizardStart ? (
        <div className="flex-1 overflow-y-auto">
          <GerarEmptyState
            onSelectContrato={selectContrato}
            onUploadContrato={handleInlineUpload}
          />
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
    </GerarWorkspace>
  );
}
