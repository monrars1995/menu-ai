function resolveApiBase(): string {
  const configured = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  const mode = (process.env.NEXT_PUBLIC_API_MODE || "auto").trim().toLowerCase();
  if (mode === "proxy" || mode === "local") return "/api-proxy";
  if (mode === "remote") return configured || "https://backend.neuros.my";

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1";
    if (!configured && isLocalhost) {
      return "/api-proxy";
    }
  }
  if (!configured) return "https://backend.neuros.my";

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1";
    const pointsToNeurosBackend = /^https:\/\/backend\.neuros\.my\/?$/i.test(configured);
    if (isLocalhost && pointsToNeurosBackend) {
      // Em localhost, usa proxy same-origin para evitar bloqueio CORS do backend de produção.
      return "/api-proxy";
    }
  }

  return configured;
}

const API_BASE = resolveApiBase();

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("menuai_token");
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "Erro desconhecido");
    throw new ApiError(text, res.status);
  }
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, senha: string) =>
      request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),
    me: () => request("/api/auth/me"),
  },

  info: () => request("/api/info"),

  llmModels: () => request("/api/llm-models"),

  empresas: {
    list: () => request("/api/empresas/"),
    get: (id: string) => request(`/api/empresas/${id}`),
    create: (data: object) => request("/api/empresas/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: object) => request(`/api/empresas/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  },

  contratos: {
    list: (params?: string) => request(`/api/contratos/${params ? `?${params}` : ""}`),
    get: (id: string) => request(`/api/contratos/${id}`),
    create: (data: object) => request("/api/contratos/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: object) => request(`/api/contratos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    upload: (id: string, file: File) => {
      const formData = new FormData();
      formData.append("arquivo", file);
      const token = getToken();
      return fetch(`${API_BASE}/api/contratos/${id}/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      }).then((r) => {
        if (!r.ok) throw new ApiError("Upload falhou", r.status);
        return r.json();
      });
    },
    analise: (id: string) => request(`/api/contratos/${id}/analise`),
    analisar: (id: string, data?: { llm_model?: string; force?: boolean }) =>
      request(`/api/contratos/${id}/analisar`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      }),
  },

  ingredientes: {
    list: (params?: string) => request(`/api/ingredientes/${params ? `?${params}` : ""}`),
    get: (id: string) => request(`/api/ingredientes/${id}`),
    create: (data: object) => request("/api/ingredientes/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: object) => request(`/api/ingredientes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    categorias: () => request("/api/ingredientes/categorias/lista"),
  },

  fichas: {
    list: (params?: string) => request(`/api/fichas-tecnicas/${params ? `?${params}` : ""}`),
    get: (id: string) => request(`/api/fichas-tecnicas/${id}`),
    create: (data: object) => request("/api/fichas-tecnicas/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: object) => request(`/api/fichas-tecnicas/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    categorias: () => request("/api/fichas-tecnicas/categorias/lista"),
    recalcular: (id: string) => request(`/api/fichas-tecnicas/${id}/recalcular`, { method: "POST" }),
    conferenciaGramatura: (contrato_id: string) => request(`/api/fichas-tecnicas/conferencia-gramatura?contrato_id=${contrato_id}`),
  },

  cardapios: {
    list: (params?: string) => request(`/api/cardapios/${params ? `?${params}` : ""}`),
    get: (id: string) => request(`/api/cardapios/${id}`),
    create: (data: object) => request("/api/cardapios/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: object) => request(`/api/cardapios/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    aprovar: (id: string, status: string, comentario?: string) =>
      request(`/api/cardapios/${id}/aprovacao`, { method: "POST", body: JSON.stringify({ cardapio_id: id, status, comentario }) }),
    publicar: (id: string) =>
      request(`/api/cardapios/${id}/publicar`, { method: "POST" }),
    exportar: (id: string, formato: string) => `${API_BASE}/api/cardapios/${id}/exportar?formato=${formato}`,
    download: (id: string, formato: string) => {
      const url = `${API_BASE}/api/cardapios/${id}/exportar?formato=${formato}`;
      const token = getToken();
      fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }).then(async (r) => {
        if (!r.ok) return;
        const blob = await r.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        const ext = formato === "pdf" ? "pdf" : formato === "csv" ? "csv" : formato === "xlsx" ? "xlsx" : "txt";
        a.download = `cardapio.${ext}`;
        a.click();
        URL.revokeObjectURL(a.href);
      });
    },
  },

  gerar: {
    start: (data: object) => request("/api/gerar", { method: "POST", body: JSON.stringify(data) }),
    status: (jobId: string) => request(`/api/status/${jobId}`),
    streamUrl: (jobId: string) => {
      const token = getToken();
      const qs = token ? `?access_token=${encodeURIComponent(token)}` : "";
      return `${API_BASE}/api/stream/${jobId}${qs}`;
    },
    download: (jobId: string, formato: string) => `${API_BASE}/api/download/${jobId}?formato=${formato}`,
    confirmar: (jobId: string, confirmar: boolean, ajustes?: string) =>
      request(`/api/gerar/${jobId}/confirmar`, {
        method: "POST",
        body: JSON.stringify({ confirmar, ajustes }),
      }),
    uploadWithFile: async (file: File, params: {
      dias: number;
      refeicoes: string[];
      target_custo_total?: number;
      restricoes_usuario?: string;
      nome_cardapio?: string;
      llm_model?: string;
      review_llm_model?: string;
      review_enabled?: boolean;
      review_strategy?: "consultive";
    }, onProgress?: (progress: number) => void) => {
      return new Promise<any>((resolve, reject) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("dias", String(params.dias));
        formData.append("refeicoes", JSON.stringify(params.refeicoes));
        if (params.target_custo_total) formData.append("target_custo_total", String(params.target_custo_total));
        if (params.restricoes_usuario) formData.append("restricoes_usuario", params.restricoes_usuario);
        if (params.nome_cardapio) formData.append("nome_cardapio", params.nome_cardapio);
        if (params.llm_model) formData.append("llm_model", params.llm_model);
        if (params.review_llm_model) formData.append("review_llm_model", params.review_llm_model);
        if (typeof params.review_enabled === "boolean") formData.append("review_enabled", String(params.review_enabled));
        if (params.review_strategy) formData.append("review_strategy", params.review_strategy);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE}/api/gerar/upload`);
        const token = getToken();
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.upload.onprogress = (event) => {
          if (!event.lengthComputable) return;
          onProgress?.(Math.round((event.loaded / event.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            onProgress?.(100);
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              resolve({});
            }
            return;
          }
          reject(new ApiError(xhr.responseText || "Erro no upload", xhr.status));
        };
        xhr.onerror = () => reject(new ApiError("Erro de rede no upload", xhr.status || 0));
        xhr.send(formData);
      });
    },
  },

  chat: {
    criarSessao: (jobId?: string) =>
      request("/api/chat/sessao", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId || null }),
      }),
    getSessao: (sessaoId: string) => request(`/api/chat/sessao/${sessaoId}`),
    refinarAnalise: (sessaoId: string, mensagem: string) =>
      request(`/api/chat/${sessaoId}/refinar_analise`, {
        method: "POST",
        body: JSON.stringify({ content: mensagem }),
      }),
    copilot: (sessaoId: string, content: string, metadata_json?: Record<string, unknown>) =>
      request(`/api/chat/${sessaoId}/copilot`, {
        method: "POST",
        body: JSON.stringify({ content, metadata_json }),
      }),
  },
};

export { ApiError, API_BASE };
export default api;
