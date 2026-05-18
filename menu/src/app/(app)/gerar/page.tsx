"use client";

import {
  ChatContainer,
  MessageBubble,
  MessageInput,
  useChatGenerator,
} from "@/components/chat";
import { GerarEmptyState } from "@/components/gerar/GerarEmptyState";
import { GerarFlowModal } from "@/components/gerar/GerarFlowModal";
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
  const hasChatInput =
    state.phase === "generating" ||
    state.phase === "result" ||
    state.phase === "error" ||
    state.phase === "hitl-confirm";
  const showFlowModal =
    state.phase === "analysis" ||
    state.phase === "upload-confirm" ||
    state.phase === "config-days" ||
    state.phase === "config-meals" ||
    state.phase === "config-cost" ||
    state.phase === "config-restrictions" ||
    state.phase === "confirm";

  return (
    <GerarWorkspace
      className="h-[calc(100dvh-11rem)] min-h-[34rem] md:h-[calc(100dvh-10rem)]"
      topBar={(
        <GerarTopBar
          llmModel={state.llmModel}
          llmModels={state.llmModels}
          loadingModels={state.loadingLlmModels}
          onChangeModel={setLlmModel}
        />
      )}
      input={!isWizardStart && hasChatInput ? (
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
      ) : undefined}
    >
      {isWizardStart ? (
        <div className="flex-1 overflow-y-auto">
          <GerarEmptyState
            onSelectContrato={selectContrato}
            onUploadContrato={handleInlineUpload}
          />
        </div>
      ) : (
        <>
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
          <GerarFlowModal
            phase={state.phase}
            open={showFlowModal}
            loading={state.loading || state.loadingAnalise}
            contratoNome={state.contratoNome}
            contratoAnalise={state.contratoAnalise}
            dias={state.dias}
            refeicoes={state.refeicoes}
            custoAlvo={state.custoAlvo}
            restricoes={state.restricoes}
            confirmData={state.confirmData}
            onAnalyzeContrato={() => analyzeContrato(undefined, undefined, true)}
            onSetDias={setDias}
            onSetRefeicoes={setRefeicoes}
            onSetCustoAlvo={setCustoAlvo}
            onSkipCost={handleSkipCost}
            onSetRestricoes={setRestricoes}
            onSkipRestrictions={handleSkipRestrictions}
            onStartGeneration={startGeneration}
            onAdjust={handleAdjust}
          />
        </>
      )}
    </GerarWorkspace>
  );
}
