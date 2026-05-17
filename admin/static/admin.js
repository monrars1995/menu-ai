/**
 * Menu.AI — painel admin: login, API com JWT, tabelas e toggles LLM
 */
const TOKEN_KEY = "menuai_admin_token";
const ADMIN_KEY_STORAGE = "menuai_admin_api_key";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getAdminApiKey() {
  return localStorage.getItem(ADMIN_KEY_STORAGE);
}

function setToken(value) {
  if (value) {
    localStorage.setItem(TOKEN_KEY, value);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function setAdminApiKey(value) {
  if (value) {
    localStorage.setItem(ADMIN_KEY_STORAGE, value);
  } else {
    localStorage.removeItem(ADMIN_KEY_STORAGE);
  }
}

function setAuthMessage(el, text, isError) {
  if (!el) return;
  el.textContent = text || "";
  el.className = isError ? "err-msg" : "muted";
}

/** @param {string} path @param {RequestInit} [options] */
async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const t = getToken();
  const apiKey = getAdminApiKey();
  if (t) {
    headers.set("Authorization", `Bearer ${t}`);
  } else if (apiKey) {
    headers.set("X-Admin-Api-Key", apiKey);
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    setToken(null);
    if (window.__onAuthRequired) {
      window.__onAuthRequired();
    }
  }
  return res;
}

function parseJsonSafe(text) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

let __meDebounce = null;
async function updateMe() {
  const meEl = document.getElementById("auth-user");
  if (!meEl) return;
  const t = getToken();
  const apiKey = getAdminApiKey();
  if (!t && !apiKey) {
    meEl.textContent = "Faça login para ver dados.";
    return;
  }
  clearTimeout(__meDebounce);
  __meDebounce = setTimeout(async () => {
    const res = await apiFetch("/api/admin/info");
    if (!res.ok) {
      meEl.textContent =
        res.status === 401
          ? "Sessão expirada ou inválida. Faça login novamente."
          : "Não foi possível carregar o usuário.";
      return;
    }
    const data = await res.json();
    const nome = data.nome || "";
    const email = data.email || "";
    const role = data.role || "";
    meEl.textContent = nome ? `${nome} (${email}) · ${role}` : `${email} · ${role}`;
  }, 50);
}

async function handleLoginSubmit(ev) {
  ev.preventDefault();
  const emailEl = document.getElementById("login-email");
  const senhaEl = document.getElementById("login-senha");
  const msgEl = document.getElementById("login-msg");
  const email = emailEl?.value?.trim();
  const senha = senhaEl?.value || "";
  if (!email || !senha) {
    setAuthMessage(msgEl, "Informe e-mail e senha.", true);
    return;
  }
  setAuthMessage(msgEl, "Entrando…");
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });
  const raw = await res.text();
  const data = parseJsonSafe(raw);
  if (!res.ok) {
    let detailMsg = "Falha no login.";
    if (data?.detail != null) {
      const d = data.detail;
      if (typeof d === "string") detailMsg = d;
      else if (Array.isArray(d))
        detailMsg = d
          .map((x) => (x && x.msg ? `${(x.loc || []).join(".")}: ${x.msg}` : JSON.stringify(x)))
          .join(" ");
      else detailMsg = JSON.stringify(d);
    } else if (raw) detailMsg = raw.slice(0, 500);
    setAuthMessage(msgEl, detailMsg, true);
    return;
  }
  if (data?.access_token) {
    setToken(data.access_token);
    setAuthMessage(msgEl, "Login realizado com sucesso.", false);
    await updateMe();
    await refreshAllLists();
    await loadLlmModels();
    highlightSidebar();
    return;
  }
  setAuthMessage(msgEl, "Resposta inesperada do servidor.", true);
}

async function handleLogout() {
  setToken(null);
  setAdminApiKey(null);
  const msgEl = document.getElementById("login-msg");
  setAuthMessage(msgEl, "Você saiu da sessão.", false);
  await updateMe();
  await loadOverview();
  await refreshAllLists();
  await loadLlmModels();
  highlightSidebar();
}

async function handleSaveAdminKey() {
  const input = document.getElementById("admin-api-key");
  const msgEl = document.getElementById("login-msg");
  const value = input?.value?.trim();
  if (!value) {
    setAuthMessage(msgEl, "Informe a chave administrativa.", true);
    return;
  }
  setToken(null);
  setAdminApiKey(value);
  const res = await apiFetch("/api/admin/info");
  if (!res.ok) {
    setAdminApiKey(null);
    setAuthMessage(msgEl, "Chave administrativa inválida ou sem utilizador de impersonação.", true);
    return;
  }
  setAuthMessage(msgEl, "Sessão administrativa iniciada com chave.", false);
  await updateMe();
  await loadOverview();
  await refreshAllLists();
  await loadLlmModels();
  highlightSidebar();
}

async function handleClearAdminKey() {
  setAdminApiKey(null);
  const input = document.getElementById("admin-api-key");
  if (input) input.value = "";
  await updateMe();
  await loadOverview();
  await refreshAllLists();
  await loadLlmModels();
}

/** Renderiza linhas em tbody a partir de objetos e chaves de coluna */
function renderTableRows(tbody, rows, columns, emptyText) {
  if (!tbody) return;
  tbody.innerHTML = "";
  if (!rows || rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = columns.length;
    td.className = "empty-msg";
    td.textContent = emptyText || "Nenhum registro.";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const col of columns) {
      const td = document.createElement("td");
      let v = row[col.key];
      if (col.fmt) v = col.fmt(v, row);
      else if (v === null || v === undefined) v = "—";
      else if (typeof v === "boolean") v = v ? "Sim" : "Não";
      td.textContent = String(v);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function fetchList(endpoint, tbodyId, columns, emptyText, limit = 20) {
  const tbody = document.getElementById(tbodyId);
  const statusEl = document.getElementById(`${tbodyId}-status`);
  if (!getToken()) {
    renderTableRows(tbody, [], columns, emptyText || "Faça login para ver dados.");
    if (statusEl) statusEl.textContent = "";
    return;
  }
  const sep = endpoint.includes("?") ? "&" : "?";
  const url = `${endpoint}${sep}skip=0&limit=${limit}`;
  const res = await apiFetch(url);
  if (!res.ok) {
    const txt = await res.text();
    renderTableRows(tbody, [], columns, "");
    if (statusEl) {
      statusEl.textContent =
        res.status === 401
          ? "Sessão expirada. Faça login novamente."
          : `Erro ${res.status}: ${txt.slice(0, 120)}`;
      statusEl.className = "err-msg";
    }
    return;
  }
  const data = await res.json();
  renderTableRows(tbody, Array.isArray(data) ? data : [], columns, emptyText);
  if (statusEl) {
    statusEl.textContent = "";
    statusEl.className = "muted";
  }
}

async function refreshAllLists() {
  await fetchList(
    "/api/empresas/",
    "tbody-empresas",
    [
      { key: "nome" },
      { key: "segmento" },
      { key: "ativo", fmt: (v) => (v ? "Sim" : "Não") },
      { key: "id", fmt: (v) => String(v).slice(0, 8) + "…" },
    ],
    "Lista vazia."
  );
  await fetchList(
    "/api/contratos/",
    "tbody-contratos",
    [
      { key: "nome" },
      { key: "numero_contrato" },
      { key: "ativo", fmt: (v) => (v ? "Sim" : "Não") },
      { key: "empresa_id", fmt: (v) => String(v).slice(0, 8) + "…" },
    ],
    "Lista vazia."
  );
  await fetchList(
    "/api/ingredientes/",
    "tbody-ingredientes",
    [
      { key: "nome" },
      { key: "categoria" },
      { key: "custo_unitario", fmt: (v) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—") },
      { key: "ativo", fmt: (v) => (v ? "Sim" : "Não") },
    ],
    "Lista vazia."
  );
  await fetchList(
    "/api/fichas-tecnicas/",
    "tbody-fichas",
    [
      { key: "nome" },
      { key: "categoria" },
      { key: "custo_porcao", fmt: (v) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—") },
      { key: "ativo", fmt: (v) => (v ? "Sim" : "Não") },
    ],
    "Lista vazia."
  );
  await fetchList(
    "/api/cardapios/",
    "tbody-cardapios",
    [
      { key: "nome" },
      { key: "status" },
      {
        key: "num_dias",
        fmt: (v) => (v != null ? String(v) : "—"),
      },
      {
        key: "custo_medio_dia",
        fmt: (v) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—"),
      },
    ],
    "Lista vazia."
  );
}

function renderOverviewCard(label, value, hint) {
  return `
    <div class="overview-card">
      <div class="overview-label">${label}</div>
      <div class="overview-value">${value}</div>
      <div class="overview-hint">${hint || "—"}</div>
    </div>
  `;
}

async function loadOverview() {
  const root = document.getElementById("overview-root");
  if (!root) return;
  if (!getToken() && !getAdminApiKey()) {
    root.innerHTML = '<p class="muted">Faça login para carregar o resumo.</p>';
    return;
  }
  const res = await apiFetch("/api/admin/meta/dashboard");
  if (!res.ok) {
    const txt = await res.text();
    root.innerHTML = `<p class="err-msg">Não foi possível carregar a visão geral: ${txt.slice(0, 180)}</p>`;
    return;
  }
  const data = await res.json();
  const counts = data.counts || {};
  const llm = data.llm || {};
  const user = data.user || {};
  const knowledge = data.knowledge || {};
  root.innerHTML = `
    <div class="overview-header">
      <div>
        <div class="overview-title">Escopo: ${data.scope || "—"}</div>
        <div class="overview-subtitle">${user.nome || "—"} · ${user.role || "—"} · ${user.email || "—"}</div>
      </div>
      <div class="overview-badge">${llm.provider || "openrouter"} · padrão ${llm.default || "—"}</div>
    </div>
    <div class="overview-grid">
      ${renderOverviewCard("Empresas", counts.empresas ?? "0", data.scope === "global" ? "visão global" : "empresa do admin")}
      ${renderOverviewCard("Contratos", counts.contratos ?? "0", "cadastros visíveis")}
      ${renderOverviewCard("Ingredientes", counts.ingredientes ?? "0", "empresa + globais")}
      ${renderOverviewCard("Fichas", counts.fichas ?? "0", "receitas ativas no escopo")}
      ${renderOverviewCard("Cardápios", counts.cardapios ?? "0", "registros persistidos")}
      ${renderOverviewCard("Jobs ativos", counts.jobs_ativos ?? "0", `${counts.jobs ?? 0} jobs totais`)}
      ${renderOverviewCard("Modelos ativos", llm.enabled_models ?? "0", `${llm.total_models ?? 0} modelos catalogados`)}
      ${renderOverviewCard("Chunks vetoriais", knowledge.chunks ?? "0", `${knowledge.chunks_embedded ?? 0} com embedding`)}
      ${renderOverviewCard("Empresa contexto", data.empresa_id || "global", "resolução da sessão")}
    </div>
  `;
}

async function loadKnowledgeStats() {
  const root = document.getElementById("knowledge-stats-root");
  if (!root) return;
  if (!getToken() && !getAdminApiKey()) {
    root.innerHTML = '<p class="muted">Faça login para carregar a base vetorial.</p>';
    return;
  }
  const res = await apiFetch("/api/admin/knowledge/stats");
  if (!res.ok) {
    const txt = await res.text();
    root.innerHTML = `<p class="err-msg">Falha ao carregar estatísticas vetoriais: ${txt.slice(0, 180)}</p>`;
    return;
  }
  const data = await res.json();
  const sourceBreakdown = (data.source_breakdown || [])
    .map((item) => `${item.source_type}: ${item.count}`)
    .join(" · ");
  root.innerHTML = `
    <div class="overview-grid">
      ${renderOverviewCard("Provider DB", data.db_provider || "—", data.vector_store_enabled ? "vector ativo" : "vector indisponível")}
      ${renderOverviewCard("Documents", data.documents ?? "0", "documentos indexados")}
      ${renderOverviewCard("Chunks", data.chunks ?? "0", `${data.chunks_embedded ?? 0} com embedding`)}
      ${renderOverviewCard("Embeddings", data.embeddings_enabled ? "on" : "off", data.semantic_search_enabled ? "busca semântica pronta" : "configure a chave")}
    </div>
    <p class="muted" style="margin-bottom:0;">${sourceBreakdown || "Sem documentos indexados."}</p>
  `;
}

async function runKnowledgeReindex() {
  const root = document.getElementById("knowledge-search-root");
  if (root) root.innerHTML = '<p class="muted">Reindexando corpus...</p>';
  const res = await apiFetch("/api/admin/knowledge/reindex", {
    method: "POST",
    body: JSON.stringify({ source_type: "all" }),
  });
  if (!res.ok) {
    const txt = await res.text();
    if (root) root.innerHTML = `<p class="err-msg">Falha na reindexação: ${txt.slice(0, 200)}</p>`;
    return;
  }
  const payload = await res.json();
  const result = payload.result || {};
  if (root) {
    root.innerHTML = `<p class="muted">Reindexação concluída: ${Object.values(result)
      .map((item) => `${item.source_type} ${item.updated}/${item.processed}`)
      .join(" · ")}</p>`;
  }
  await loadKnowledgeStats();
  await loadOverview();
}

async function searchKnowledge() {
  const root = document.getElementById("knowledge-search-root");
  const query = document.getElementById("knowledge-query")?.value?.trim() || "";
  const sourceType = document.getElementById("knowledge-source-type")?.value || "";
  if (!query) {
    if (root) root.innerHTML = '<p class="err-msg">Informe uma consulta para a busca semântica.</p>';
    return;
  }
  if (root) root.innerHTML = '<p class="muted">Pesquisando...</p>';
  const res = await apiFetch("/api/admin/knowledge/search", {
    method: "POST",
    body: JSON.stringify({ query, source_type: sourceType || null, limit: 5 }),
  });
  if (!res.ok) {
    const txt = await res.text();
    if (root) root.innerHTML = `<p class="err-msg">Falha na busca semântica: ${txt.slice(0, 200)}</p>`;
    return;
  }
  const payload = await res.json();
  const rows = payload.results || [];
  if (!rows.length) {
    root.innerHTML = '<p class="muted">Nenhum resultado semântico encontrado.</p>';
    return;
  }
  root.innerHTML = rows
    .map((row) => {
      const chunk = String(row.chunk_text || "").replace(/\n+/g, " ").slice(0, 280);
      return `
        <div class="llm-row">
          <div class="llm-info">
            <div class="llm-title">${row.title || row.source_type || "Trecho"}</div>
            <div class="muted" style="font-size:0.82rem;">${row.source_type || "—"} · similaridade ${Number(row.similarity || 0).toFixed(3)}</div>
            <div class="llm-desc">${chunk}</div>
          </div>
        </div>
      `;
    })
    .join("");
}

async function loadLlmModels() {
  const root = document.getElementById("llm-models-root");
  if (!root) return;
  if (!getToken() && !getAdminApiKey()) {
    root.innerHTML =
      '<p class="muted">Faça login para gerenciar os modelos LLM.</p>';
    return;
  }
  const res = await apiFetch("/api/admin/llm-models");
  if (!res.ok) {
    root.innerHTML =
      '<p class="err-msg">Não foi possível carregar os modelos. Verifique permissões de administrador.</p>';
    return;
  }
  const payload = await res.json();
  const models = payload.models || [];
  root.innerHTML = "";
  if (!models.length) {
    root.innerHTML = '<p class="muted">Nenhum modelo no catálogo.</p>';
    return;
  }
  const meta = document.createElement("p");
  meta.className = "muted";
  meta.style.marginTop = "0";
  meta.textContent = `Provedor: ${payload.provider || "—"} · Padrão: ${payload.default || "—"}`;
  root.appendChild(meta);

  for (const m of models) {
    const row = document.createElement("div");
    row.className = "llm-row";

    const info = document.createElement("div");
    info.className = "llm-info";
    const title = document.createElement("div");
    title.className = "llm-title";
    title.style.fontWeight = "500";
    title.textContent = m.label || m.id;
    const sub = document.createElement("div");
    sub.className = "muted";
    sub.style.fontSize = "0.82rem";
    sub.textContent = `${m.id}${m.provider ? ` · ${m.provider}` : ""}${m.model_string ? ` · ${m.model_string}` : m.slug ? ` · ${m.slug}` : ""}`;
    info.appendChild(title);
    info.appendChild(sub);
    if (m.description) {
      const desc = document.createElement("div");
      desc.className = "llm-desc";
      desc.textContent = m.description;
      info.appendChild(desc);
    }
    if (payload.default === m.id) {
      const badge = document.createElement("span");
      badge.className = "inline-badge";
      badge.textContent = "Padrão";
      title.appendChild(document.createTextNode(" "));
      title.appendChild(badge);
    }

    const label = document.createElement("label");
    label.className = "switch";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !!m.enabled;
    cb.dataset.modelId = m.id;
    const slider = document.createElement("span");
    slider.className = "slider";
    label.appendChild(cb);
    label.appendChild(slider);

    cb.addEventListener("change", async () => {
      cb.disabled = true;
      const r = await apiFetch(`/api/admin/llm-models/${encodeURIComponent(m.id)}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: cb.checked }),
      });
      cb.disabled = false;
      if (!r.ok) {
        cb.checked = !cb.checked;
        const err = await r.text();
        alert(`Não foi possível atualizar o modelo: ${err.slice(0, 200)}`);
      }
    });

    row.appendChild(info);
    row.appendChild(label);
    root.appendChild(row);
  }
}

function highlightSidebar() {
  const hash = (window.location.hash || "#login").slice(1);
  document.querySelectorAll(".sidebar-link").forEach((a) => {
    const id = a.getAttribute("href")?.slice(1);
    a.classList.toggle("active", id === hash);
  });
}

function setupSidebarObserver() {
  const ids = [
    "login",
    "overview",
    "empresas",
    "contratos",
    "ingredientes",
    "fichas",
    "cardapios",
    "pipeline",
    "llm",
    "knowledge",
    "docs",
  ];
  const observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting && e.intersectionRatio > 0.25) {
          const id = e.target.id;
          if (!id) continue;
          document.querySelectorAll(".sidebar-link").forEach((a) => {
            const href = a.getAttribute("href")?.slice(1);
            a.classList.toggle("active", href === id);
          });
        }
      }
    },
    { root: null, threshold: [0.25, 0.5], rootMargin: `-70px 0px -50% 0px` }
  );
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });
}

window.__onAuthRequired = () => {
  updateMe();
  loadOverview();
  refreshAllLists();
  loadLlmModels();
  loadKnowledgeStats();
};

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  if (form) form.addEventListener("submit", handleLoginSubmit);

  const logoutBtn = document.getElementById("btn-logout");
  if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);

  const saveAdminKeyBtn = document.getElementById("btn-save-admin-key");
  if (saveAdminKeyBtn) saveAdminKeyBtn.addEventListener("click", handleSaveAdminKey);

  const clearAdminKeyBtn = document.getElementById("btn-clear-admin-key");
  if (clearAdminKeyBtn) clearAdminKeyBtn.addEventListener("click", handleClearAdminKey);

  const apiKeyInput = document.getElementById("admin-api-key");
  if (apiKeyInput) {
    apiKeyInput.value = getAdminApiKey() || "";
  }

  const refreshBtn = document.getElementById("btn-refresh-data");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      await loadOverview();
      await refreshAllLists();
      await loadLlmModels();
      await loadKnowledgeStats();
    });
  }

  const refreshKnowledgeBtn = document.getElementById("btn-refresh-knowledge");
  if (refreshKnowledgeBtn) refreshKnowledgeBtn.addEventListener("click", loadKnowledgeStats);

  const reindexKnowledgeBtn = document.getElementById("btn-reindex-knowledge");
  if (reindexKnowledgeBtn) reindexKnowledgeBtn.addEventListener("click", runKnowledgeReindex);

  const searchKnowledgeBtn = document.getElementById("btn-search-knowledge");
  if (searchKnowledgeBtn) searchKnowledgeBtn.addEventListener("click", searchKnowledge);

  window.addEventListener("hashchange", highlightSidebar);

  updateMe();
  loadOverview();
  refreshAllLists();
  loadLlmModels();
  loadKnowledgeStats();
  highlightSidebar();
  setupSidebarObserver();

  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
});
