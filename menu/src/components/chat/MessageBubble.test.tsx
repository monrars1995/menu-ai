import { render, screen } from "@testing-library/react";
import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("mostra a label da etapa e percentual no rail de pipeline", () => {
    render(
      <MessageBubble
        role="agent"
        type="pipeline"
        content=""
        pipelineStep={3}
        pipelineProgress={45}
      />
    );

    expect(screen.getByText("Montando cardapio")).toBeInTheDocument();
    expect(screen.getByText("45%")).toBeInTheDocument();
  });

  it("mantem o card HITL de confirmacao no pipeline", () => {
    render(
      <MessageBubble
        role="agent"
        type="pipeline"
        content=""
        pipelineStep={2}
        pipelineProgress={30}
        hitlData={{ jobId: "job-123", resumo: "Resumo de teste" }}
        onConfirmHitl={vi.fn()}
      />
    );

    expect(screen.getByText("Analise do Contrato Concluida")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar e Continuar" })).toBeInTheDocument();
  });
});
