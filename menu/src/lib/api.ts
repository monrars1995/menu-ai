const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://backend.neuros.my";

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
      request(`/api/cardapios/${id}/aprovacao`, { method: "POST", body: JSON.stringify({ status, comentario }) }),
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
    streamUrl: (jobId: string) => `${API_BASE}/api/stream/${jobId}`,
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
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("dias", String(params.dias));
      formData.append("refeicoes", JSON.stringify(params.refeicoes));
      if (params.target_custo_total) formData.append("target_custo_total", String(params.target_custo_total));
      if (params.restricoes_usuario) formData.append("restricoes_usuario", params.restricoes_usuario);
      if (params.nome_cardapio) formData.append("nome_cardapio", params.nome_cardapio);
      if (params.llm_model) formData.append("llm_model", params.llm_model);
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/gerar/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "Erro no upload");
        throw new ApiError(text, res.status);
      }
      return res.json();
    },
  },
};

export { ApiError, API_BASE };
export default api;
