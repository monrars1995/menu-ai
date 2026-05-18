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

  it("renderiza analise com listas estruturadas sem quebrar React", () => {
    render(
      <MessageBubble
        role="agent"
        type="analysis"
        content="Analise pronta"
        analysis={{
          status: "analisado",
          necessidades: { observacoes: "ok", num_refeicoes_dia: 1, estrutura_refeicao: {} },
          servicos: { num_refeicoes_dia: 1, estrutura: {} },
          gramaturas: { proteico: "120g", regra: { nome: "salada", tipo: "livre" } as any },
          incidencias: {},
          proibicoes: [{ nome: "peixe", tipo: "proibido", frequencia: "0", regras: "contrato" } as any],
          restricoes_alergenos: [{ nome: "gluten" } as any],
          dietas_especiais: [{ nome: "vegetariano", tipo: "dieta", frequencia: "diario", regras: "obrigatoria" } as any],
          sazonalidade: false,
        }}
      />
    );

    expect(screen.getByText("Analise do Contrato")).toBeInTheDocument();
    expect(screen.getByText(/vegetariano/i)).toBeInTheDocument();
    expect(screen.getByText(/peixe/i)).toBeInTheDocument();
  });
});
