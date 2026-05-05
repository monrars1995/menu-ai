"use client";

import { useState, useRef, useEffect } from "react";
import api, { API_BASE } from "@/lib/api";
import type { Contrato, ContratoAnalise, Cardapio } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChatPhase =
  | "welcome"
  | "analysis"
  | "config-days"
  | "config-meals"
  | "config-cost"
  | "config-restrictions"
  | "confirm"
  | "generating"
  | "hitl-confirm"
  | "result"
  | "error"
  | "uploading";

export type MessageType =
  | "text"
  | "analysis"
  | "pipeline"
  | "confirm"
  | "result"
  | "error"
  | "uploading";

export interface ChatMessage {
  id: string;
  role: "agent" | "user";
  type: MessageType;
  content: string;
  timestamp: number;
  analysis?: ContratoAnalise | null;
  pipelineStep?: number;
  pipelineProgress?: number;
  pensamento?: string;
  confirmData?: ConfirmData;
  hitlData?: {
    resumo: any;
    jobId: string;
  };
  resultData?: ResultData;
  erro?: string;
}

export interface ConfirmData {
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  contratoNome: string;
}

export interface ResultData {
  jobId: string;
  cardapioId: string;
  nome: string;
  numDias: number;
  custoMedioDia: number;
}

export interface ChatState {
  phase: ChatPhase;
  messages: ChatMessage[];
  contratos: Contrato[];
  contratoId: string;
  contratoAnalise: ContratoAnalise | null;
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  jobId: string | null;
  sessaoId: string | null;
  cardapioId: string | null;
  loading: boolean;
  loadingContratos: boolean;
  loadingAnalise: boolean;
}

const DEFAULT_REFEICOES = ["almoco", "jantar"];

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChatGenerator() {
  const eventSourceRef = useRef<EventSource | null>(null);

  // Refs to avoid stale closures in SSE callbacks
  const stateRef = useRef<ChatState | null>(null);

  const [state, setState] = useState<ChatState>({
    phase: "welcome",
    messages: [],
    contratos: [],
    contratoId: "",
    contratoAnalise: null,
    dias: 5,
    refeicoes: DEFAULT_REFEICOES,
    custoAlvo: "",
    restricoes: "",
    jobId: null,
    sessaoId: null,
    cardapioId: null,
    loading: false,
    loadingContratos: true,
    loadingAnalise: false,
  });

  // Keep ref in sync
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Load contracts on mount
  useEffect(() => {
    api.contratos
      .list()
      .then((r) => {
        setState((s) => ({
          ...s,
          contratos: r.items || [],
          loadingContratos: false,
        }));
      })
      .catch(() => {
        setState((s) => ({ ...s, loadingContratos: false }));
      });

    // Welcome message
    addAgentMessage(
      "text",
      "Ola! Vou te ajudar a gerar um cardapio inteligente. Comece selecionando um contrato existente ou fazendo upload do PDF."
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function addAgentMessage(
    type: MessageType,
    content: string,
    extras: Partial<ChatMessage> = {}
  ): string {
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const msg: ChatMessage = {
      id,
      role: "agent",
      type,
      content,
      timestamp: Date.now(),
      ...extras,
    };
    setState((s) => ({ ...s, messages: [...s.messages, msg] }));
    return id;
  }

  function addUserMessage(content: string): string {
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const msg: ChatMessage = {
      id,
      role: "user",
      type: "text",
      content,
      timestamp: Date.now(),
    };
    setState((s) => ({ ...s, messages: [...s.messages, msg] }));
    return id;
  }

  function updateLastAgentMessage(
    updater: (msg: ChatMessage) => Partial<ChatMessage>
  ) {
    setState((s) => {
      const msgs = [...s.messages];
      // findLastIndex fallback for older targets
      let idx = -1;
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "agent") { idx = i; break; }
      }
      if (idx === -1) return s;
      msgs[idx] = { ...msgs[idx], ...updater(msgs[idx]) };
      return { ...s, messages: msgs };
    });
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  function selectContrato(id: string) {
    const s = stateRef.current!;
    const contrato = s.contratos.find((c) => c.id === id);
    const nome = contrato?.nome || id;

    addUserMessage(`Contrato selecionado: ${nome}`);

    setState((prev) => ({
      ...prev,
      contratoId: id,
      loadingAnalise: true,
    }));

    api.contratos
      .analise(id)
      .then((analise) => {
        setState((prev) => ({ ...prev, contratoAnalise: analise }));
        addAgentMessage(
          "analysis",
          `Analisei o contrato "${nome}". Aqui esta o que entendi:`,
          { analysis: analise }
        );
        setState((prev) => ({
          ...prev,
          phase: "config-days",
          loadingAnalise: false,
        }));
        setTimeout(() => {
          addAgentMessage("text", "Para quantos dias deseja o cardapio?");
        }, 400);
      })
      .catch(() => {
        addAgentMessage(
          "analysis",
          `Contrato "${nome}" selecionado. A analise sera feita durante a geracao.`,
          { analysis: null }
        );
        setState((prev) => ({
          ...prev,
          phase: "config-days",
          loadingAnalise: false,
        }));
        setTimeout(() => {
          addAgentMessage("text", "Para quantos dias deseja o cardapio?");
        }, 400);
      });
  }

  function goToUpload() {
    addUserMessage("Quero fazer upload de um contrato.");
    addAgentMessage(
      "text",
      "Para fazer upload de um PDF, va a pagina de Contratos. Apos o upload, selecione o contrato aqui."
    );
    if (typeof window !== "undefined") {
      window.location.href = "/contratos";
    }
  }

  function handleInlineUpload(file: File) {
    const s = stateRef.current!;

    addUserMessage(`Enviando: ${file.name}`);
    setState((prev) => ({ ...prev, phase: "uploading", loading: true }));
    addAgentMessage("uploading", `Enviando ${file.name}...`);

    api.gerar
      .uploadWithFile(file, {
        dias: s.dias,
        refeicoes: s.refeicoes,
        target_custo_total: s.custoAlvo ? parseFloat(s.custoAlvo) : undefined,
        restricoes_usuario: s.restricoes || undefined,
      })
      .then((res) => {
        const { job_id, contrato_id, contrato_nome, novo_contrato } = res;

        setState((prev) => ({
          ...prev,
          contratoId: contrato_id,
          jobId: job_id,
          loading: false,
        }));

        if (novo_contrato) {
          addAgentMessage("text", `Contrato "${contrato_nome}" cadastrado com sucesso!`);
        } else {
          addAgentMessage("text", `Contrato "${contrato_nome}" encontrado.`);
        }

        api.contratos
          .analise(contrato_id)
          .then((analise) => {
            setState((prev) => ({ ...prev, contratoAnalise: analise }));
            addAgentMessage("analysis", "Analise do contrato:", { analysis: analise });
            setState((prev) => ({ ...prev, phase: "config-days" }));
            setTimeout(() => {
              addAgentMessage("text", "Para quantos dias deseja o cardapio?");
            }, 400);
          })
          .catch(() => {
            addAgentMessage("analysis", "Analise sera feita durante a geracao.", { analysis: null });
            setState((prev) => ({ ...prev, phase: "config-days" }));
            setTimeout(() => {
              addAgentMessage("text", "Para quantos dias deseja o cardapio?");
            }, 400);
          });
      })
      .catch((e) => {
        setState((prev) => ({ ...prev, phase: "welcome", loading: false }));
        addAgentMessage("error", e.message || "Erro ao enviar arquivo. Tente novamente.");
      });
  }

  function setDias(value: number) {
    const clamped = Math.min(30, Math.max(1, value));
    addUserMessage(`${clamped} dias`);
    setState((s) => ({ ...s, dias: clamped, phase: "config-meals" }));
    setTimeout(() => {
      addAgentMessage("text", "Quais refeicoes deseja incluir?");
    }, 400);
  }

  function setRefeicoes(value: string[]) {
    if (value.length === 0) return;
    const labels = value
      .map((v) => {
        const map: Record<string, string> = {
          cafe_manha: "Cafe da Manha",
          almoco: "Almoco",
          lanche_tarde: "Lanche da Tarde",
          jantar: "Jantar",
          lanche_manha: "Lanche da Manha",
          ceia: "Ceia",
        };
        return map[v] || v;
      })
      .join(", ");
    addUserMessage(`Refeicoes: ${labels}`);
    setState((s) => ({ ...s, refeicoes: value, phase: "config-cost" }));
    setTimeout(() => {
      addAgentMessage(
        "text",
        "Qual o custo alvo diario em R$? (opcional - pode pular)"
      );
    }, 400);
  }

  function setCustoAlvo(value: string) {
    if (value === "") {
      addUserMessage("Sem custo alvo");
    } else {
      addUserMessage(`Custo alvo: R$ ${value}`);
    }
    setState((s) => ({ ...s, custoAlvo: value, phase: "config-restrictions" }));
    setTimeout(() => {
      addAgentMessage(
        "text",
        "Ha alguma restricao adicional? (ex: sem gluten, vegano - pode pular)"
      );
    }, 400);
  }

  function setRestricoes(value: string) {
    if (value.trim() === "") {
      addUserMessage("Sem restricoes adicionais");
    } else {
      addUserMessage(`Restricoes: ${value}`);
    }
    setState((s) => ({ ...s, restricoes: value, phase: "confirm" }));
    setTimeout(() => {
      const s = stateRef.current!;
      const contratoNome =
        s.contratos.find((c) => c.id === s.contratoId)?.nome ||
        "Nenhum contrato";
      const confirmData: ConfirmData = {
        dias: s.dias,
        refeicoes: s.refeicoes,
        custoAlvo: s.custoAlvo,
        restricoes: value,
        contratoNome,
      };
      addAgentMessage(
        "confirm",
        "Pronto! Confira os parametros antes de gerar:",
        { confirmData }
      );
    }, 400);
  }

  function handleSkipCost() {
    setCustoAlvo("");
  }

  function handleSkipRestrictions() {
    setRestricoes("");
  }

  function handleAdjust() {
    setState((s) => ({ ...s, phase: "config-days" }));
    addAgentMessage("text", "Para quantos dias deseja o cardapio?");
  }

  function startGeneration() {
    addUserMessage("Gerar cardapio!");

    const s = stateRef.current!;
    setState((prev) => ({ ...prev, phase: "generating", loading: true }));

    addAgentMessage(
      "pipeline",
      "Gerando cardapio...",
      { pipelineStep: 0, pipelineProgress: 0 }
    );

    const data = {
      dias: s.dias,
      contrato_id: s.contratoId || undefined,
      target_custo_total: s.custoAlvo
        ? parseFloat(s.custoAlvo)
        : undefined,
      restricoes_usuario: s.restricoes || undefined,
      refeicoes: s.refeicoes,
    };

    api.gerar
      .start(data)
      .then((res) => {
        const jobId = res.job_id as string;
        setState((prev) => ({ ...prev, jobId }));
        connectStream(jobId);

        // Criar sessão de chat vinculada ao job
        api.chat.criarSessao(jobId).then((sessao) => {
          setState((prev) => ({ ...prev, sessaoId: sessao.id }));
        }).catch(console.error);
      })
      .catch((e) => {
        setState((s) => ({ ...s, phase: "error", loading: false }));
        addAgentMessage(
          "error",
          `Erro ao iniciar geracao: ${e.message || "Tente novamente."}`
        );
      });
  }

  function connectStream(jobId: string) {
    if (eventSourceRef.current) eventSourceRef.current.close();

    const es = new EventSource(`${API_BASE}/api/stream/${jobId}`);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        updateLastAgentMessage((msg) => {
          const updates: Partial<ChatMessage> = {};
          if (data.step !== undefined) updates.pipelineStep = data.step;
          if (data.progresso !== undefined)
            updates.pipelineProgress = data.progresso;
          if (data.pensamento) updates.pensamento = data.pensamento;
          if (data.type === "aguardando_confirmacao") {
            updates.hitlData = {
              resumo: data.resumo,
              jobId: jobId,
            };
          }
          if (data.status === "concluido") {
            updates.pipelineStep = 7;
            updates.pipelineProgress = 100;

            api.cardapios
              .list(`job_id=${jobId}`)
              .then((r) => {
                if (r.items?.[0]) {
                  const item = r.items[0] as Cardapio;
                  const s = stateRef.current!;
                  const resultData: ResultData = {
                    jobId,
                    cardapioId: item.id,
                    nome: item.nome || "Cardapio",
                    numDias: item.num_dias || s.dias,
                    custoMedioDia: item.custo_medio_dia || 0,
                  };
                  setState((prev) => ({
                    ...prev,
                    phase: "result",
                    loading: false,
                    cardapioId: item.id,
                  }));
                  addAgentMessage(
                    "result",
                    "Cardapio gerado com sucesso!",
                    { resultData }
                  );
                }
              })
              .catch(() => {
                const s = stateRef.current!;
                setState((prev) => ({
                  ...prev,
                  phase: "result",
                  loading: false,
                }));
                addAgentMessage(
                  "result",
                  "Cardapio gerado com sucesso!",
                  {
                    resultData: {
                      jobId,
                      cardapioId: "",
                      nome: "Cardapio",
                      numDias: s.dias,
                      custoMedioDia: 0,
                    },
                  }
                );
              });
          }
          if (data.erro || data.status === "erro") {
            setState((s) => ({ ...s, phase: "error", loading: false }));
            updates.erro = data.erro || "Erro na geracao";
            updates.content = updates.erro;
            updates.type = "error";
          }
          return updates;
        });

        if (data.type === "aguardando_confirmacao") {
          setState((s) => ({ ...s, phase: "hitl-confirm" }));
        }

        if (data.status === "concluido" || data.status === "erro") {
          es.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      api.gerar
        .status(jobId)
        .then((s) => {
          if (s.status === "concluido") {
            setState((prev) => ({ ...prev, phase: "result", loading: false }));
            api.cardapios
              .list(`job_id=${jobId}`)
              .then((r) => {
                if (r.items?.[0]) {
                  const item = r.items[0] as Cardapio;
                  const resultData: ResultData = {
                    jobId,
                    cardapioId: item.id,
                    nome: item.nome || "Cardapio",
                    numDias: item.num_dias || stateRef.current!.dias,
                    custoMedioDia: item.custo_medio_dia || 0,
                  };
                  addAgentMessage(
                    "result",
                    "Cardapio gerado com sucesso!",
                    { resultData }
                  );
                }
              })
              .catch(() => {});
          } else if (s.status === "erro") {
            setState((prev) => ({ ...prev, phase: "error", loading: false }));
            addAgentMessage("error", s.erro || "Erro na geracao");
          } else {
            setTimeout(() => connectStream(jobId), 2000);
          }
        })
        .catch(() => {
          setState((s) => ({ ...s, phase: "error", loading: false }));
        });
    };

    eventSourceRef.current = es;
  }

  function handleNewGeneration() {
    if (eventSourceRef.current) eventSourceRef.current.close();
    setState((s) => ({
      ...s,
      phase: "welcome",
      messages: [],
      contratoId: "",
      contratoAnalise: null,
      dias: 5,
      refeicoes: DEFAULT_REFEICOES,
      custoAlvo: "",
      restricoes: "",
      jobId: null,
      sessaoId: null,
      cardapioId: null,
      loading: false,
    }));
    addAgentMessage(
      "text",
      "Ola! Vou te ajudar a gerar um cardapio inteligente. Comece selecionando um contrato existente ou fazendo upload do PDF."
    );
  }

  function confirmHitl(confirm: boolean, ajustes?: string) {
    const s = stateRef.current!;
    if (!s.jobId) return;

    setState((prev) => ({ ...prev, loading: true }));
    api.gerar
      .confirmar(s.jobId, confirm, ajustes)
      .then(() => {
        if (!confirm) {
          setState((prev) => ({ ...prev, phase: "error", loading: false }));
          addAgentMessage("error", "Geracao cancelada pelo usuario.");
          if (eventSourceRef.current) eventSourceRef.current.close();
        } else {
          setState((prev) => ({ ...prev, phase: "generating", loading: false }));
          addUserMessage(
            ajustes
              ? `Confirmado com ajustes: ${ajustes}`
              : "Contrato confirmado. Pode continuar."
          );
          updateLastAgentMessage(() => ({ hitlData: undefined })); // hide the card
        }
      })
      .catch((e) => {
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("error", `Erro ao confirmar: ${e.message}`);
      });
  }

  function sendChatMessage(text: string) {
    if (!text.trim()) return;
    const s = stateRef.current!;
    if (!s.sessaoId) {
      addAgentMessage("error", "Sessão de chat não encontrada.");
      return;
    }

    addUserMessage(text);
    setState((prev) => ({ ...prev, loading: true }));

    api.chat.refinarAnalise(s.sessaoId, text)
      .then(() => {
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("pipeline", "Refinando análise...", { pensamento: "Processando as novas instruções e ajustando o contexto do contrato..." });
      })
      .catch((e) => {
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("error", `Erro ao enviar mensagem: ${e.message}`);
      });
  }

  return {
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
  };
}
