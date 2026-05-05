"use client";

import {
  ChatContainer,
  MessageBubble,
  MessageInput,
  useChatGenerator,
} from "@/components/chat";

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
  } = useChatGenerator();

  return (
    <div className="flex min-h-0 flex-1 flex-col">
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

      {/* Input area */}
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
      />
    </div>
  );
}
