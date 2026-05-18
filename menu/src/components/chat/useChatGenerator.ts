"use client";

import { useState, useRef, useEffect } from "react";
import api, { API_BASE } from "@/lib/api";
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
  errorType?: string;
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
  status?: string;
  preview?: CardapioPreviewDay[];
  warnings?: string[];
}

export interface CardapioPreviewDay {
  dia: number;
  refeicao: string;
  proteicos: string[];
  acompanhamentos: string[];
  saladas: string[];
  sobremesa?: string;
  bebida?: string;
  fruta?: string;
  tema?: string;
  custo?: number;
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
  contratoAnaliseConfirmada: boolean;
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  confirmData: ConfirmData | null;
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
const DEFAULT_TIMEOUT_BUDGET_SECONDS = 300;
const STALE_SYNC_WARNING_MS = 45000;
const STALE_SYNC_TIMEOUT_MS = 240000;

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

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChatGenerator() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const didInitRef = useRef(false);
  const streamRetryCountRef = useRef<Record<string, number>>({});
  const pollRetryCountRef = useRef<Record<string, number>>({});
  const activePipelineMessageIdRef = useRef<string | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  const finalizedJobsRef = useRef<Record<string, boolean>>({});
  const generationStartedAtRef = useRef<number | null>(null);
  const lastRealtimeUpdateRef = useRef<number>(0);
  const lastStatusSignatureRef = useRef<string>("");
  const lastBackendProgressAtRef = useRef<number>(0);
  const staleWarningMsRef = useRef<number>(STALE_SYNC_WARNING_MS);
  const staleTimeoutMsRef = useRef<number>(STALE_SYNC_TIMEOUT_MS);

  // Refs to avoid stale closures in SSE callbacks
  const stateRef = useRef<ChatState | null>(null);

  const [state, setState] = useState<ChatState>({
    phase: "welcome",
    messages: [],
    contratos: [],
    contratoId: "",
    contratoNome: "",
    contratoAnalise: null,
    contratoAnaliseConfirmada: false,
    dias: 5,
    refeicoes: DEFAULT_REFEICOES,
    custoAlvo: "",
    restricoes: "",
    confirmData: null,
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
    if (didInitRef.current) return;
    didInitRef.current = true;

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

    // Fluxo inicia no modal embutido (sem bolha introdutória redundante).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function normalizeApiError(error: unknown, fallback: string): string {
    const raw = (error as any)?.message ? String((error as any).message) : "";
    if (!raw) return fallback;
    try {
      const parsed = JSON.parse(raw);
      const detail = typeof parsed?.detail === "string" ? parsed.detail.trim() : "";
      const msg = typeof parsed?.message === "string" ? parsed.message.trim() : "";
      const value = detail || msg;
      if (value) {
        if (value.toLowerCase().includes("unsupported value: 'temperature'")) {
          return "O modelo selecionado recusou parâmetro de temperatura. Já aplicamos fallback automático; tente novamente.";
        }
        return value;
      }
    } catch {
      // ignore parse error
    }
    if (raw.toLowerCase().includes("unsupported value: 'temperature'")) {
      return "O modelo selecionado recusou parâmetro de temperatura. Já aplicamos fallback automático; tente novamente.";
    }
    return raw;
  }

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
      const patch = updater(msgs[idx]);
      if (!patch || Object.keys(patch).length === 0) return s;
      const hasChange = Object.entries(patch).some(([k, v]) => (msgs[idx] as any)[k] !== v);
      if (!hasChange) return s;
      msgs[idx] = { ...msgs[idx], ...patch };
      return { ...s, messages: msgs };
    });
  }

  function updateMessage(
    id: string,
    updater: (msg: ChatMessage) => Partial<ChatMessage>
  ) {
    setState((s) => {
      let changed = false;
      const nextMessages = s.messages.map((msg) => {
        if (msg.id !== id) return msg;
        const patch = updater(msg);
        if (!patch || Object.keys(patch).length === 0) return msg;
        const hasChange = Object.entries(patch).some(([k, v]) => (msg as any)[k] !== v);
        if (!hasChange) return msg;
        changed = true;
        return { ...msg, ...patch };
      });
      return changed ? { ...s, messages: nextMessages } : s;
    });
  }

  function shouldUsePollingTransport(): boolean {
    const forced = (process.env.NEXT_PUBLIC_STREAM_TRANSPORT || "").trim().toLowerCase();
    if (forced === "polling") return true;
    if (forced === "sse") return false;
    // Default: prioriza SSE para experiência em tempo real.
    // Polling fica como fallback automático em erro de stream.
    return false;
  }

  function clearPollTimer() {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  function clearHeartbeatTimer() {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }

  function clearActiveGenerationRefs() {
    activePipelineMessageIdRef.current = null;
    activeJobIdRef.current = null;
    generationStartedAtRef.current = null;
    lastRealtimeUpdateRef.current = 0;
    lastStatusSignatureRef.current = "";
    lastBackendProgressAtRef.current = 0;
    staleWarningMsRef.current = STALE_SYNC_WARNING_MS;
    staleTimeoutMsRef.current = STALE_SYNC_TIMEOUT_MS;
    clearHeartbeatTimer();
  }

  function applyStaleThresholdFromBudget(timeoutBudgetSeconds?: number) {
    const budget = Number.isFinite(timeoutBudgetSeconds)
      ? Math.max(60, Number(timeoutBudgetSeconds))
      : DEFAULT_TIMEOUT_BUDGET_SECONDS;
    const timeoutMs = Math.max(120000, Math.min(280000, Math.floor(budget * 1000 * 0.88)));
    const warningMs = Math.max(30000, Math.min(90000, Math.floor(timeoutMs * 0.35)));
    staleTimeoutMsRef.current = timeoutMs;
    staleWarningMsRef.current = warningMs;
  }

  function failActiveGeneration(message: string, errorType = "stale_job_timeout") {
    const activeJob = activeJobIdRef.current;
    if (activeJob && finalizedJobsRef.current[activeJob]) return;
    if (activeJob) finalizedJobsRef.current[activeJob] = true;
    updateActivePipelineMessage(() => ({
      type: "error",
      content: message,
      erro: message,
      errorType,
    }));
    setState((s) => ({ ...s, phase: "error", loading: false }));
    clearActiveGenerationRefs();
    clearPollTimer();
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }

  function markJobFinalized(jobId: string): boolean {
    if (finalizedJobsRef.current[jobId]) return false;
    finalizedJobsRef.current[jobId] = true;
    return true;
  }

  function updateActivePipelineMessage(
    updater: (msg: ChatMessage) => Partial<ChatMessage>
  ) {
    const currentId = activePipelineMessageIdRef.current;
    if (currentId) {
      updateMessage(currentId, updater);
      return;
    }
    updateLastAgentMessage(updater);
  }

  function formatElapsed(startedAt: number): string {
    const elapsedSec = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    const min = Math.floor(elapsedSec / 60);
    const sec = elapsedSec % 60;
    return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  function startLiveHeartbeat(jobId: string) {
    clearHeartbeatTimer();
    heartbeatTimerRef.current = setInterval(() => {
      if (!activeJobIdRef.current || activeJobIdRef.current !== jobId) return;
      const startedAt = generationStartedAtRef.current;
      if (!startedAt) return;
      const elapsed = formatElapsed(startedAt);
      const staleMs = lastRealtimeUpdateRef.current
        ? Date.now() - lastRealtimeUpdateRef.current
        : 0;
      const timeoutMs = staleTimeoutMsRef.current;
      const warningMs = staleWarningMsRef.current;

      if (staleMs >= timeoutMs) {
        failActiveGeneration(
          "O servidor não atualizou o progresso dentro do tempo esperado. Tente novamente, troque o modelo ou reduza os dias.",
          "timeout_budget_exceeded"
        );
        return;
      }

      updateActivePipelineMessage((msg) => {
        const baseContent = msg.content?.startsWith("Gerando cardapio")
          ? msg.content.split(" • ")[0]
          : "Gerando cardapio...";
        const content = `${baseContent} • ${elapsed}`;
        if (staleMs > warningMs) {
          return {
            content,
            pensamento:
              "Sincronização degradada: sem atualização recente do backend. Tentando recuperar...",
          };
        }
        return { content };
      });
    }, 1000);
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

  function pipelineStepFromProgressWithContext(progress: number, skipContractAnalysis: boolean): number {
    const step = pipelineStepFromProgress(progress);
    if (!skipContractAnalysis) return step;
    // Se o contrato já foi analisado/confirmado antes de gerar, evita voltar visualmente para etapa 0
    return Math.max(1, step);
  }

  function buildCardapioPreview(cardapio: Cardapio): CardapioPreviewDay[] {
    const days = [...(cardapio.dias || [])].sort((a, b) => Number(a.numero_dia || 0) - Number(b.numero_dia || 0));
    const preview: CardapioPreviewDay[] = [];
    for (const day of days) {
      const byMeal = new Map<string, NonNullable<Cardapio["dias"]>[number]["refeicoes"]>();
      for (const ref of day.refeicoes || []) {
        const key = ref.tipo_refeicao || "almoco";
        const current = byMeal.get(key) || [];
        current.push(ref);
        byMeal.set(key, current);
      }
      for (const [meal, refs = []] of byMeal) {
        const byCategory = (needle: string) =>
          refs
            .filter((r) => String(r.categoria || "").toLowerCase().includes(needle))
            .map((r) => String(r.nome_prato || r.ficha_tecnica_nome || "").trim())
            .filter(Boolean);
        const exact = (name: string) =>
          refs.find((r) => String(r.categoria || "").toLowerCase() === name.toLowerCase())?.nome_prato;
        const includesAny = (...needles: string[]) =>
          refs
            .filter((r) => needles.some((n) => String(r.categoria || "").toLowerCase().includes(n)))
            .map((r) => String(r.nome_prato || r.ficha_tecnica_nome || "").trim())
            .filter(Boolean);
        preview.push({
          dia: Number(day.numero_dia || preview.length + 1),
          refeicao: meal.replace(/_/g, " "),
          proteicos: byCategory("proteic"),
          acompanhamentos: includesAny("arroz", "feij", "guarni", "acompanhamento", "pão", "recheio"),
          saladas: byCategory("salada"),
          sobremesa: exact("Sobremesa"),
          bebida: exact("Bebida") || exact("Bebida Café"),
          fruta: exact("Fruta") || exact("Fruta Café"),
          tema: undefined,
          custo: Number(day.custo_total || 0),
        });
      }
    }
    return preview.slice(0, 30);
  }

  function validationWarnings(cardapio: Cardapio): string[] {
    const raw = cardapio.parametros_json?.validation_warnings;
    return Array.isArray(raw) ? raw.map((x) => String(x)).filter(Boolean).slice(0, 5) : [];
  }

  function resultDataFromCardapio(jobId: string, cardapio: Cardapio): ResultData {
    const s = stateRef.current!;
    return {
      jobId,
      cardapioId: cardapio.id,
      nome: cardapio.nome || "Cardapio",
      numDias: cardapio.num_dias || s.dias,
      custoMedioDia: cardapio.custo_medio_dia || 0,
      status: cardapio.status,
      preview: buildCardapioPreview(cardapio),
      warnings: validationWarnings(cardapio),
    };
  }

  function resolveGenerationResult(jobId: string) {
    api.cardapios
      .list(`job_id=${jobId}`)
      .then(async (r) => {
        const s = stateRef.current!;
        const item = r.items?.[0] as Cardapio | undefined;
        let detailed: Cardapio | null = item || null;
        if (item?.id) {
          try {
            detailed = (await api.cardapios.get(item.id)) as Cardapio;
          } catch {
            detailed = item;
          }
        }
        const resultData: ResultData = detailed
          ? resultDataFromCardapio(jobId, detailed)
          : item
          ? resultDataFromCardapio(jobId, item)
          : {
              jobId,
              cardapioId: "",
              nome: "Cardapio",
              numDias: s.dias,
              custoMedioDia: 0,
            };
        clearActiveGenerationRefs();
        setState((prev) => ({
          ...prev,
          phase: "result",
          loading: false,
          cardapioId: item?.id || null,
        }));
        addAgentMessage(
          "result",
          "Cardápio gerado. Revise a prévia abaixo e escolha se deseja aprovar ou gerar novamente.",
          { resultData }
        );
      })
      .catch(() => {
        const s = stateRef.current!;
        clearActiveGenerationRefs();
        setState((prev) => ({ ...prev, phase: "result", loading: false }));
        addAgentMessage("result", "Cardápio gerado. Revise a prévia abaixo e escolha se deseja aprovar ou gerar novamente.", {
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
      contratoAnaliseConfirmada: true,
      phase: "config-days",
      loadingAnalise: false,
      loading: false,
      confirmData: null,
    }));
    addAgentMessage(
      "analysis",
      `Analisei o contrato "${nome}". Aqui esta o que entendi:`,
      { analysis: analise }
    );
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

    if (!force) {
      api.contratos
        .analise(contratoId)
        .then((analiseExistente) => {
          if (analiseExistente?.status === "analisado") {
            finishContratoAnalysis(contratoId, contratoNome, analiseExistente);
            return;
          }
          runContratoAnalysis();
        })
        .catch(() => {
          runContratoAnalysis();
        });
      return;
    }

    runContratoAnalysis();

    function runContratoAnalysis() {
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
          const message = normalizeApiError(e, "Erro ao analisar contrato.");
          setState((prev) => ({
            ...prev,
            phase: "error",
            loading: false,
            loadingAnalise: false,
          }));
          updateMessage(progressMsgId, () => ({
            type: "error",
            content: message,
            erro: message,
          }));
        });
    }
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
        const { contrato_id, contrato_nome, analise_status } = res;

        setState((prev) => ({
          ...prev,
          messages: prev.messages.filter((msg) => msg.id !== uploadMsgId),
          contratoId: contrato_id,
          contratoNome: contrato_nome,
          contratoAnaliseConfirmada: analise_status === "analisado",
          phase: "upload-confirm",
          loading: false,
          confirmData: null,
        }));
      })
      .catch((e) => {
        setState((prev) => ({ ...prev, phase: "error", loading: false }));
        addAgentMessage("error", normalizeApiError(e, "Erro ao enviar arquivo. Tente novamente."));
      });
  }

  function setDias(value: number) {
    const clamped = Math.min(30, Math.max(1, value));
    addUserMessage(`${clamped} dias`);
    setState((s) => ({ ...s, dias: clamped, phase: "config-meals", confirmData: null }));
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
    setState((s) => ({ ...s, refeicoes: value, phase: "config-cost", confirmData: null }));
  }

  function setCustoAlvo(value: string) {
    if (value === "") {
      addUserMessage("Sem custo alvo");
    } else {
      addUserMessage(`Custo alvo: R$ ${value}`);
    }
    setState((s) => ({ ...s, custoAlvo: value, phase: "config-restrictions", confirmData: null }));
  }

  function setRestricoes(value: string) {
    if (value.trim() === "") {
      addUserMessage("Sem restricoes adicionais");
    } else {
      addUserMessage(`Restricoes: ${value}`);
    }
    setState((s) => {
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
      return { ...s, restricoes: value, phase: "confirm", confirmData };
    });
  }

  function handleSkipCost() {
    setCustoAlvo("");
  }

  function handleSkipRestrictions() {
    setRestricoes("");
  }

  function handleAdjust() {
    setState((s) => ({ ...s, phase: "config-days", confirmData: null }));
  }

  function startGeneration() {
    const s = stateRef.current!;
    if (s.loading && s.phase === "generating") {
      addAgentMessage("text", "A geracao ja esta em andamento. Aguarde a conclusao.");
      return;
    }

    addUserMessage("Gerar cardapio!");

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    clearPollTimer();

    const skipContractAnalysis = Boolean(
      s.contratoAnaliseConfirmada ||
      s.contratoAnalise?.status === "analisado" ||
      buildContratoRestricoesFixas(s.contratoAnalise)
    );
    setState((prev) => ({ ...prev, phase: "generating", loading: true }));

    const pipelineMsgId = addAgentMessage(
      "pipeline",
      "Gerando cardapio...",
      { pipelineStep: skipContractAnalysis ? 1 : 0, pipelineProgress: 0 }
    );
    activePipelineMessageIdRef.current = pipelineMsgId;
    activeJobIdRef.current = null;

    const data = {
      dias: s.dias,
      contrato_id: s.contratoId || undefined,
      target_custo_total: s.custoAlvo
        ? parseFloat(s.custoAlvo)
        : undefined,
      restricoes_usuario: buildRestricoesPayload(s.contratoAnalise, s.restricoes),
      refeicoes: s.refeicoes,
      llm_model: s.llmModel || undefined,
      contrato_analise_confirmada: skipContractAnalysis,
      generation_mode: "fast",
    };
    applyStaleThresholdFromBudget(DEFAULT_TIMEOUT_BUDGET_SECONDS);

    api.gerar
      .start(data)
      .then((res) => {
        const jobId = res.job_id as string;
        finalizedJobsRef.current[jobId] = false;
        activeJobIdRef.current = jobId;
        generationStartedAtRef.current = Date.now();
        lastRealtimeUpdateRef.current = Date.now();
        lastBackendProgressAtRef.current = Date.now();
        lastStatusSignatureRef.current = "";
        streamRetryCountRef.current[jobId] = 0;
        startLiveHeartbeat(jobId);
        setState((prev) => ({ ...prev, jobId }));
        if (shouldUsePollingTransport()) {
          pollJobStatus(jobId, skipContractAnalysis);
        } else {
          connectStream(jobId, skipContractAnalysis);
          // Watchdog de status para não travar visualmente se o SSE cair em proxies/CDN.
          setTimeout(() => pollJobStatus(jobId, skipContractAnalysis), 1200);
        }

        // Criar sessão de chat vinculada ao job
        api.chat.criarSessao(jobId).then((sessao) => {
          setState((prev) => ({ ...prev, sessaoId: sessao.id }));
        }).catch(console.error);
      })
      .catch((e) => {
        const message = normalizeApiError(e, "Erro ao iniciar geracao.");
        setState((s) => ({ ...s, phase: "error", loading: false }));
        updateActivePipelineMessage(() => ({
          type: "error",
          content: `Erro ao iniciar geracao: ${message}`,
          erro: message,
        }));
        clearActiveGenerationRefs();
      });
  }

  function pollJobStatus(jobId: string, skipContractAnalysis = false) {
    if (activeJobIdRef.current && activeJobIdRef.current !== jobId) return;
    clearPollTimer();

    const tick = () => {
      api.gerar
        .status(jobId)
        .then((snapshot) => {
          pollRetryCountRef.current[jobId] = 0;
          const progress = Number(snapshot?.progress ?? 0) || 0;
          const status = String(snapshot?.status || "");
          const erro = snapshot?.error;
          const errorType = snapshot?.error_type;
          const currentStep = snapshot?.current_step ? String(snapshot.current_step) : "";
          const lastUpdateAtToken = snapshot?.last_update_at ? String(snapshot.last_update_at) : "";
          const signature = [status, progress, currentStep, lastUpdateAtToken, String(errorType || ""), String(erro || "")].join("|");
          if (signature !== lastStatusSignatureRef.current) {
            lastStatusSignatureRef.current = signature;
            lastRealtimeUpdateRef.current = Date.now();
            lastBackendProgressAtRef.current = Date.now();
          }

          const backendLastUpdateAt = snapshot?.last_update_at ? Date.parse(String(snapshot.last_update_at)) : NaN;
          const timeoutBudgetSeconds = Number(snapshot?.timeout_budget_seconds || DEFAULT_TIMEOUT_BUDGET_SECONDS);
          applyStaleThresholdFromBudget(timeoutBudgetSeconds);
          if (status === "executando") {
            const staleByBackend = Number.isFinite(backendLastUpdateAt)
              ? Date.now() - Number(backendLastUpdateAt)
              : 0;
            const staleBySignature = lastBackendProgressAtRef.current
              ? Date.now() - lastBackendProgressAtRef.current
              : 0;
            if (Math.max(staleByBackend, staleBySignature) > staleTimeoutMsRef.current) {
              failActiveGeneration(
                "Geração parada no backend por tempo excessivo. Tente novamente, troque o modelo ou reduza os dias.",
                "timeout_budget_exceeded"
              );
              return;
            }
          }

          updateActivePipelineMessage((msg) => {
            const updates: Partial<ChatMessage> = {
              pipelineProgress: progress,
              pipelineStep: pipelineStepFromProgressWithContext(progress, skipContractAnalysis),
            };
            if (erro) {
              updates.type = "error";
              updates.content = String(erro);
              updates.erro = String(erro);
              updates.errorType = errorType ? String(errorType) : "generation_failed";
            }
            if (snapshot?.current_step) {
              updates.pensamento = String(snapshot.current_step);
            }
            return updates;
          });

          if (status === "aguardando_confirmacao") {
            setState((s) => ({ ...s, phase: "hitl-confirm", loading: false }));
          } else if (status === "concluido") {
            clearPollTimer();
            if (markJobFinalized(jobId)) {
              resolveGenerationResult(jobId);
            }
            return;
          } else if (status === "erro") {
            clearPollTimer();
            clearActiveGenerationRefs();
            markJobFinalized(jobId);
            setState((s) => ({ ...s, phase: "error", loading: false }));
            if (erro) {
              addAgentMessage("error", String(erro), {
                erro: String(erro),
                errorType: errorType ? String(errorType) : "generation_failed",
              });
            }
            return;
          }

          pollTimerRef.current = setTimeout(tick, 2500);
        })
        .catch((error) => {
          const statusCode = Number((error as any)?.status || 0);
          if (statusCode === 401) {
            failActiveGeneration(
              "Sua sessão expirou durante a geração. Faça login novamente e tente de novo.",
              "auth_required"
            );
            return;
          }
          const retries = (pollRetryCountRef.current[jobId] || 0) + 1;
          pollRetryCountRef.current[jobId] = retries;
          updateActivePipelineMessage(() => ({
            pensamento:
              retries >= 4
                ? "Nao consegui ler o progresso em tempo real. Tentando reconectar automaticamente..."
                : "Conexao instavel no streaming. Tentando sincronizar progresso...",
          }));
          pollTimerRef.current = setTimeout(tick, retries >= 4 ? 4500 : 3000);
        });
    };

    tick();
  }

  function connectStream(jobId: string, skipContractAnalysis = false) {
    if (eventSourceRef.current) eventSourceRef.current.close();

    const es = new EventSource(api.gerar.streamUrl(jobId));

    function finishSuccess() {
      streamRetryCountRef.current[jobId] = 0;
      clearPollTimer();
      if (markJobFinalized(jobId)) {
        resolveGenerationResult(jobId);
      }
    }

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        lastRealtimeUpdateRef.current = Date.now();
        if (data.type === "ping") return;
        streamRetryCountRef.current[jobId] = 0;
        if (activeJobIdRef.current && activeJobIdRef.current !== jobId) {
          return;
        }
        updateActivePipelineMessage((msg) => {
          const updates: Partial<ChatMessage> = {};
          const progress = data.progress ?? data.progresso;
          if (data.step !== undefined) updates.pipelineStep = data.step;
          if (progress !== undefined) {
            updates.pipelineProgress = progress;
            if (data.step === undefined) {
              updates.pipelineStep = pipelineStepFromProgressWithContext(
                progress,
                skipContractAnalysis
              );
            }
          }
          if (data.message && data.type === "log") updates.pensamento = String(data.message).slice(0, 220);
          if (data.current_step) updates.pensamento = String(data.current_step).slice(0, 220);
          if (data.pensamento) updates.pensamento = String(data.pensamento).slice(0, 220);
          if (data.thought) updates.pensamento = String(data.thought).slice(0, 220);
          if (data.preview) updates.pensamento = String(data.preview).slice(0, 220);
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
            updates.errorType = data.error_type || "generation_failed";
          }
          return updates;
        });

        if (data.type === "aguardando_confirmacao") {
          setState((s) => ({ ...s, phase: "hitl-confirm", loading: false }));
        }

        if (data.type === "done" || data.status === "concluido") {
          es.close();
          finishSuccess();
        }

        if (data.type === "error" || data.status === "erro") {
          es.close();
          markJobFinalized(jobId);
          clearActiveGenerationRefs();
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      const retries = (streamRetryCountRef.current[jobId] || 0) + 1;
      streamRetryCountRef.current[jobId] = retries;
      if (retries >= 2) {
        pollJobStatus(jobId, skipContractAnalysis);
        return;
      }
      api.gerar
        .status(jobId)
        .then((s) => {
          if (s.status === "concluido") {
            clearActiveGenerationRefs();
            if (!markJobFinalized(jobId)) return;
            setState((prev) => ({ ...prev, phase: "result", loading: false }));
            api.cardapios
              .list(`job_id=${jobId}`)
              .then(async (r) => {
                if (r.items?.[0]) {
                  const item = r.items[0] as Cardapio;
                  let detailed = item;
                  if (item.id) {
                    try {
                      detailed = (await api.cardapios.get(item.id)) as Cardapio;
                    } catch {
                      detailed = item;
                    }
                  }
                  const resultData: ResultData = resultDataFromCardapio(jobId, detailed);
                  addAgentMessage(
                    "result",
                    "Cardápio gerado. Revise a prévia abaixo e escolha se deseja aprovar ou gerar novamente.",
                    { resultData }
                  );
                }
              })
              .catch(() => {});
          } else if (s.status === "erro") {
            clearActiveGenerationRefs();
            markJobFinalized(jobId);
            setState((prev) => ({ ...prev, phase: "error", loading: false }));
            const message = s.error || "Erro na geracao";
            addAgentMessage("error", message, {
              erro: message,
              errorType: s.error_type || "generation_failed",
            });
          } else {
            setTimeout(() => connectStream(jobId, skipContractAnalysis), 2000);
          }
        })
        .catch((error) => {
          const statusCode = Number((error as any)?.status || 0);
          if (statusCode === 401) {
            failActiveGeneration(
              "Sua sessão expirou durante a geração. Faça login novamente e tente de novo.",
              "auth_required"
            );
            return;
          }
          failActiveGeneration(
            "Falha ao recuperar status de geração. Verifique a conexão com a API e tente novamente.",
            "status_sync_failed"
          );
        });
    };

    eventSourceRef.current = es;
  }

  function handleNewGeneration() {
    if (eventSourceRef.current) eventSourceRef.current.close();
    clearPollTimer();
    clearActiveGenerationRefs();
    setState((s) => ({
      ...s,
      phase: "welcome",
      messages: [],
      contratoId: "",
      contratoNome: "",
      contratoAnalise: null,
      contratoAnaliseConfirmada: false,
      dias: 5,
      refeicoes: DEFAULT_REFEICOES,
      custoAlvo: "",
      restricoes: "",
      confirmData: null,
      jobId: null,
      sessaoId: null,
      cardapioId: null,
      loading: false,
    }));
    // Reinicia direto no modal de início, sem mensagem introdutória.
  }

  function regenerateCardapio() {
    if (eventSourceRef.current) eventSourceRef.current.close();
    clearPollTimer();
    clearActiveGenerationRefs();
    startGeneration();
  }

  function retryAfterTimeout() {
    const s = stateRef.current!;
    if (s.loading) return;
    addUserMessage("Tentar novamente");
    startGeneration();
  }

  function switchModelAfterTimeout() {
    const s = stateRef.current!;
    if (!s.llmModels.length) return;
    const currentIndex = Math.max(0, s.llmModels.findIndex((m) => m.id === s.llmModel));
    const nextModel = s.llmModels[(currentIndex + 1) % s.llmModels.length];
    if (!nextModel?.id) return;
    setLlmModel(nextModel.id);
    addAgentMessage("text", `Modelo alterado para ${nextModel.label || nextModel.id}.`);
  }

  function reduceDaysAfterTimeout() {
    const s = stateRef.current!;
    const reduced = Math.max(7, Math.min(21, Math.floor(s.dias * 0.7)));
    const nextDays = reduced === s.dias ? Math.max(1, s.dias - 5) : reduced;
    setState((prev) => ({ ...prev, dias: nextDays }));
    addAgentMessage("text", `Dias reduzidos para ${nextDays}. Você pode tentar novamente agora.`);
  }

  function approveGeneratedCardapio(cardapioId: string) {
    if (!cardapioId) {
      addAgentMessage("error", "Cardápio ainda não está disponível para aprovação.");
      return;
    }
    addUserMessage("Aprovar cardápio");
    setState((prev) => ({ ...prev, loading: true }));
    api.cardapios
      .aprovar(cardapioId, "aprovado", "Aprovado pelo chat de geração.")
      .then(() => {
        setState((prev) => ({
          ...prev,
          loading: false,
          messages: prev.messages.map((msg) =>
            msg.resultData?.cardapioId === cardapioId
              ? { ...msg, resultData: { ...msg.resultData, status: "aprovado" } }
              : msg
          ),
        }));
        addAgentMessage("text", "Cardápio aprovado. Você já pode baixar ou consultar o registro completo.");
      })
      .catch((e) => {
        const message = normalizeApiError(e, "Não foi possível aprovar o cardápio.");
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("error", message);
      });
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
        const message = normalizeApiError(e, "Erro ao confirmar.");
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("error", `Erro ao confirmar: ${message}`);
      });
  }

  function sendChatMessage(text: string) {
    const cleanText = text.trim();
    if (!cleanText) return;
    const s = stateRef.current!;

    if (s.phase === "generating") {
      addAgentMessage("text", "A geracao esta em andamento. Aguarde concluir para pedir ajustes.");
      return;
    }

    if (s.phase === "hitl-confirm") {
      const normalized = cleanText.toLowerCase();
      const noAdjustCommands = new Set([
        "ok",
        "sim",
        "continue",
        "continuar",
        "pode seguir",
        "segue",
        "prosseguir",
        "confirmo",
      ]);
      const ajustes = noAdjustCommands.has(normalized) ? undefined : cleanText;
      confirmHitl(true, ajustes);
      return;
    }

    if (!s.sessaoId) {
      addAgentMessage("error", "Sessão de chat não encontrada.");
      return;
    }

    addUserMessage(cleanText);
    setState((prev) => ({ ...prev, loading: true }));

    api.chat.refinarAnalise(s.sessaoId, cleanText)
      .then(() => {
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage(
          "text",
          "Entendi os ajustes. Eles serao considerados na proxima geracao."
        );
      })
      .catch((e) => {
        const message = normalizeApiError(e, "Erro ao enviar mensagem.");
        setState((prev) => ({ ...prev, loading: false }));
        addAgentMessage("error", `Erro ao enviar mensagem: ${message}`);
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
    regenerateCardapio,
    retryAfterTimeout,
    switchModelAfterTimeout,
    reduceDaysAfterTimeout,
    approveGeneratedCardapio,
    setLlmModel,
    confirmHitl,
    sendChatMessage,
  };
}
