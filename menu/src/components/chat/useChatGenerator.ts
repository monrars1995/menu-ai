"use client";

import { useState, useRef, useEffect } from "react";
import api from "@/lib/api";
import type { Contrato, ContratoAnalise, Cardapio, LlmModel } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChatPhase =
  | "welcome"
  | "analysis"
  | "upload-confirm"
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
  | "uploading"
  | "upload-ready";

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
  uploadData?: UploadData;
  uploadProgress?: number;
  erro?: string;
}

export interface ConfirmData {
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  restricoesContrato?: string;
  restricoesAdicionais?: string;
  contratoNome: string;
  modeloLabel?: string;
}

export interface ResultData {
  jobId: string;
  cardapioId: string;
  nome: string;
  numDias: number;
  custoMedioDia: number;
}

export interface UploadData {
  contratoId: string;
  contratoNome: string;
  novoContrato?: boolean;
  tamanhoKb?: number;
  analiseStatus?: string;
}

export interface ChatState {
  phase: ChatPhase;
  messages: ChatMessage[];
  contratos: Contrato[];
  contratoId: string;
  contratoNome: string;
  contratoAnalise: ContratoAnalise | null;
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  llmModel: string;
  llmModels: LlmModel[];
  loadingLlmModels: boolean;
  jobId: string | null;
  sessaoId: string | null;
  cardapioId: string | null;
  loading: boolean;
  loadingContratos: boolean;
  loadingAnalise: boolean;
}

const DEFAULT_REFEICOES = ["almoco", "jantar"];
const LLM_MODEL_STORAGE_KEY = "menuai_llm_model";

function _cleanList(items?: string[] | Record<string, unknown>): string[] {
  if (!items) return [];
  const raw = Array.isArray(items)
    ? items
    : Object.entries(items).map(([key, value]) => `${key}: ${String(value)}`);
  if (!raw.length) return [];
  return Array.from(
    new Set(
      raw
        .map((x) => String(x || "").trim())
        .filter(Boolean)
    )
  );
}

function buildContratoRestricoesFixas(analise: ContratoAnalise | null): string {
  if (!analise) return "";
  const dietas = _cleanList(analise.dietas_especiais);
  const proibicoes = _cleanList(analise.proibicoes);
  const alergenos = _cleanList(analise.restricoes_alergenos);
  const incidencias = _cleanList(analise.incidencias);
  const linhas: string[] = [];
  if (dietas.length) linhas.push(`Dietas especiais do contrato: ${dietas.join(", ")}`);
  if (proibicoes.length) linhas.push(`Proibicoes do contrato: ${proibicoes.join(", ")}`);
  if (alergenos.length) linhas.push(`Alergenos/restricoes do contrato: ${alergenos.join(", ")}`);
  if (incidencias.length) linhas.push(`Incidencias obrigatorias do contrato: ${incidencias.join(", ")}`);
  return linhas.join("\n");
}

function buildRestricoesPayload(analise: ContratoAnalise | null, adicionais: string): string | undefined {
  const fixas = buildContratoRestricoesFixas(analise);
  const extra = (adicionais || "").trim();
  const blocos: string[] = [];
  if (fixas) blocos.push(`=== REGRAS FIXAS DO CONTRATO ===\n${fixas}`);
  if (extra) blocos.push(`=== RESTRICOES ADICIONAIS DO USUARIO ===\n${extra}`);
  const finalTxt = blocos.join("\n\n").trim();
  return finalTxt || undefined;
}

function getPerguntaRestricoes(analise: ContratoAnalise | null): string {
  const fixas = buildContratoRestricoesFixas(analise);
  if (fixas) {
    return "As restricoes do contrato ja serao aplicadas automaticamente. Deseja adicionar alguma restricao extra? (opcional)";
  }
  return "Ha alguma restricao adicional? (ex: sem gluten, vegano - pode pular)";
}

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
    contratoNome: "",
    contratoAnalise: null,
    dias: 5,
    refeicoes: DEFAULT_REFEICOES,
    custoAlvo: "",
    restricoes: "",
    llmModel: "",
    llmModels: [],
    loadingLlmModels: true,
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

    api.llmModels()
      .then((payload) => {
        const models = (payload.models || []) as LlmModel[];
        const defaultModel = models.length ? String(payload.default || models[0]?.id || "") : "";
        const savedModel =
          typeof window !== "undefined"
            ? window.localStorage.getItem(LLM_MODEL_STORAGE_KEY)
            : null;
        const selected =
          savedModel && models.some((m) => m.id === savedModel)
            ? savedModel
            : defaultModel;
        if (selected && typeof window !== "undefined") {
          window.localStorage.setItem(LLM_MODEL_STORAGE_KEY, selected);
        }
        setState((s) => ({
          ...s,
          llmModels: models,
          llmModel: selected,
          loadingLlmModels: false,
        }));
      })
      .catch(() => {
        setState((s) => ({ ...s, loadingLlmModels: false }));
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

  function updateMessage(
    id: string,
    updater: (msg: ChatMessage) => Partial<ChatMessage>
  ) {
    setState((s) => ({
      ...s,
      messages: s.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updater(msg) } : msg
      ),
    }));
  }

  function pipelineStepFromProgress(progress: number): number {
    if (progress >= 100) return 7;
    if (progress >= 92) return 6;
    if (progress >= 75) return 5;
    if (progress >= 60) return 4;
    if (progress >= 45) return 3;
    if (progress >= 30) return 2;
    if (progress >= 15) return 1;
    return 0;
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
      contratoNome: nome,
      phase: "analysis",
      loadingAnalise: true,
    }));

    api.contratos
      .analise(id)
      .then((analise) => {
        if (analise?.status === "analisado") {
          finishContratoAnalysis(id, nome, analise);
        } else {
          analyzeContrato(id, nome);
        }
      })
      .catch(() => {
        analyzeContrato(id, nome);
      });
  }

  function finishContratoAnalysis(id: string, nome: string, analise: ContratoAnalise) {
    setState((prev) => ({
      ...prev,
      contratoId: id,
      contratoNome: nome,
      contratoAnalise: analise,
      phase: "config-days",
      loadingAnalise: false,
      loading: false,
    }));
    addAgentMessage(
      "analysis",
      `Analisei o contrato "${nome}". Aqui esta o que entendi:`,
      { analysis: analise }
    );
    setTimeout(() => {
      addAgentMessage("text", "Para quantos dias deseja o cardapio?");
    }, 400);
  }

  function analyzeContrato(id?: string, nome?: string, force = false) {
    const s = stateRef.current!;
    const contratoId = id || s.contratoId;
    const contratoNome =
      nome ||
      s.contratoNome ||
      s.contratos.find((c) => c.id === contratoId)?.nome ||
      "Contrato";
    if (!contratoId) return;

    setState((prev) => ({
      ...prev,
      contratoId,
      contratoNome,
      phase: "analysis",
      loading: true,
      loadingAnalise: true,
    }));

    const progressMsgId = addAgentMessage(
      "pipeline",
      "Analisando contrato...",
      { pipelineStep: 0, pipelineProgress: 15 }
    );

    api.contratos
      .analisar(contratoId, { llm_model: s.llmModel || undefined, force })
      .then((analise) => {
        updateMessage(progressMsgId, () => ({
          pipelineStep: 7,
          pipelineProgress: 100,
          content: "Analise do contrato concluida.",
        }));
        finishContratoAnalysis(contratoId, contratoNome, analise);
      })
      .catch((e) => {
        setState((prev) => ({
          ...prev,
          phase: "error",
          loading: false,
          loadingAnalise: false,
        }));
        updateMessage(progressMsgId, () => ({
          type: "error",
          content: e.message || "Erro ao analisar contrato.",
          erro: e.message || "Erro ao analisar contrato.",
        }));
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
    const uploadMsgId = addAgentMessage("uploading", `Enviando ${file.name}...`, {
      uploadProgress: 0,
    });

    api.gerar
      .uploadWithFile(file, {
        dias: s.dias,
        refeicoes: s.refeicoes,
        target_custo_total: s.custoAlvo ? parseFloat(s.custoAlvo) : undefined,
        restricoes_usuario: buildRestricoesPayload(s.contratoAnalise, s.restricoes),
        llm_model: s.llmModel || undefined,
      }, (progress) => {
        updateMessage(uploadMsgId, () => ({
          uploadProgress: progress,
          content: progress >= 100 ? "Upload 100% concluido." : `Enviando ${file.name}... ${progress}%`,
        }));
      })
      .then((res) => {
        const { contrato_id, contrato_nome, novo_contrato, tamanho_kb, analise_status } = res;

        setState((prev) => ({
          ...prev,
          contratoId: contrato_id,
          contratoNome: contrato_nome,
          phase: "upload-confirm",
          loading: false,
        }));

        addAgentMessage(
          "upload-ready",
          novo_contrato
            ? `Contrato "${contrato_nome}" carregado.`
            : `Contrato "${contrato_nome}" encontrado na base.`,
          {
            uploadData: {
              contratoId: contrato_id,
              contratoNome: contrato_nome,
              novoContrato: novo_contrato,
              tamanhoKb: tamanho_kb,
              analiseStatus: analise_status,
            },
          }
        );
      })
      .catch((e) => {
        setState((prev) => ({ ...prev, phase: "error", loading: false }));
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
      const s = stateRef.current!;
      addAgentMessage("text", getPerguntaRestricoes(s.contratoAnalise));
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
      const restricoesContrato = buildContratoRestricoesFixas(s.contratoAnalise);
      const restricoesAdicionais = (value || "").trim();
      const restricoesPayload = buildRestricoesPayload(s.contratoAnalise, value) || "";
      const confirmData: ConfirmData = {
        dias: s.dias,
        refeicoes: s.refeicoes,
        custoAlvo: s.custoAlvo,
        restricoes: restricoesPayload,
        restricoesContrato: restricoesContrato || undefined,
        restricoesAdicionais: restricoesAdicionais || undefined,
        contratoNome,
        modeloLabel:
          s.llmModels.find((m) => m.id === s.llmModel)?.label ||
          s.llmModel ||
          undefined,
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
      restricoes_usuario: buildRestricoesPayload(s.contratoAnalise, s.restricoes),
      refeicoes: s.refeicoes,
      llm_model: s.llmModel || undefined,
      contrato_analise_confirmada: s.contratoAnalise?.status === "analisado",
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

    const es = new EventSource(api.gerar.streamUrl(jobId));

    function finishSuccess() {
      api.cardapios
        .list(`job_id=${jobId}`)
        .then((r) => {
          const s = stateRef.current!;
          const item = r.items?.[0] as Cardapio | undefined;
          const resultData: ResultData = item
            ? {
                jobId,
                cardapioId: item.id,
                nome: item.nome || "Cardapio",
                numDias: item.num_dias || s.dias,
                custoMedioDia: item.custo_medio_dia || 0,
              }
            : {
                jobId,
                cardapioId: "",
                nome: "Cardapio",
                numDias: s.dias,
                custoMedioDia: 0,
              };
          setState((prev) => ({
            ...prev,
            phase: "result",
            loading: false,
            cardapioId: item?.id || null,
          }));
          addAgentMessage("result", "Cardapio gerado com sucesso!", { resultData });
        })
        .catch(() => {
          const s = stateRef.current!;
          setState((prev) => ({ ...prev, phase: "result", loading: false }));
          addAgentMessage("result", "Cardapio gerado com sucesso!", {
            resultData: {
              jobId,
              cardapioId: "",
              nome: "Cardapio",
              numDias: s.dias,
              custoMedioDia: 0,
            },
          });
        });
    }

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        updateLastAgentMessage((msg) => {
          const updates: Partial<ChatMessage> = {};
          const progress = data.progress ?? data.progresso;
          if (data.step !== undefined) updates.pipelineStep = data.step;
          if (progress !== undefined) {
            updates.pipelineProgress = progress;
            if (data.step === undefined) updates.pipelineStep = pipelineStepFromProgress(progress);
          }
          if (data.message && data.type === "log") updates.pensamento = data.message;
          if (data.pensamento) updates.pensamento = data.pensamento;
          if (data.thought) updates.pensamento = data.thought;
          if (data.preview) updates.pensamento = data.preview;
          if (data.type === "aguardando_confirmacao") {
            updates.hitlData = {
              resumo: data.resumo,
              jobId: jobId,
            };
          }
          if (data.type === "done" || data.status === "concluido") {
            updates.pipelineStep = 7;
            updates.pipelineProgress = 100;
          }
          if (data.erro || data.error || data.type === "error" || data.status === "erro") {
            setState((s) => ({ ...s, phase: "error", loading: false }));
            updates.erro = data.erro || data.error || data.message || "Erro na geracao";
            updates.content = updates.erro;
            updates.type = "error";
          }
          return updates;
        });

        if (data.type === "aguardando_confirmacao") {
          setState((s) => ({ ...s, phase: "hitl-confirm" }));
        }

        if (data.type === "done" || data.status === "concluido") {
          es.close();
          finishSuccess();
        }

        if (data.type === "error" || data.status === "erro") {
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
            addAgentMessage("error", s.erro || s.error || "Erro na geracao");
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
      contratoNome: "",
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

  function setLlmModel(modelId: string) {
    if (!modelId) return;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LLM_MODEL_STORAGE_KEY, modelId);
    }
    setState((s) => ({ ...s, llmModel: modelId }));
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
    setLlmModel,
    confirmHitl,
    sendChatMessage,
  };
}
