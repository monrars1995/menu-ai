"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { BrainCircuit, Search, RotateCcw } from "lucide-react";

interface KnowledgeStats {
  db_provider?: string;
  vector_store_enabled?: boolean;
  documents?: number;
  chunks?: number;
  chunks_embedded?: number;
  embeddings_enabled?: boolean;
  semantic_search_enabled?: boolean;
  source_breakdown?: { source_type: string; count: number }[];
}

interface SearchResult {
  title?: string;
  source_type?: string;
  similarity?: number;
  chunk_text?: string;
}

export default function KnowledgePage() {
  const { apiFetch } = useApi();
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [searching, setSearching] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    setLoadingStats(true);
    const res = await apiFetch("/api/admin/knowledge/stats");
    if (res.ok) {
      const data = await res.json();
      setStats(data);
    }
    setLoadingStats(false);
  }

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    const res = await apiFetch("/api/admin/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query, limit: 5 }),
    });
    if (res.ok) {
      const data = await res.json();
      setResults(data.results || []);
    }
    setSearching(false);
  }

  async function handleReindex() {
    setReindexing(true);
    await apiFetch("/api/admin/knowledge/reindex", {
      method: "POST",
      body: JSON.stringify({ source_type: "all" }),
    });
    setReindexing(false);
    loadStats();
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-page-title">Knowledge Base</h1>
        <p className="text-subtitle">
          {stats ? `Provider: ${stats.db_provider || "—"} · ${stats.vector_store_enabled ? "Vector ativo" : "Vector indisponível"}` : "Carregando…"}
        </p>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MiniStat label="Documents" value={stats?.documents ?? 0} loading={loadingStats} />
        <MiniStat label="Chunks" value={stats?.chunks ?? 0} hint={`${stats?.chunks_embedded ?? 0} com embedding`} loading={loadingStats} />
        <MiniStat label="Embeddings" value={stats?.embeddings_enabled ? "on" : "off"} loading={loadingStats} />
        <MiniStat label="Busca" value={stats?.semantic_search_enabled ? "pronta" : "indisponível"} loading={loadingStats} />
      </div>

      {/* Actions */}
      <div className="mb-4 flex items-center gap-2">
        <button onClick={handleReindex} disabled={reindexing} className="btn-secondary text-xs">
          <RotateCcw size={14} className={reindexing ? "animate-spin" : ""} />
          {reindexing ? "Reindexando…" : "Reindexar"}
        </button>
      </div>

      {/* Search */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Busca semântica…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="input-subtle flex-1"
        />
        <button onClick={handleSearch} disabled={searching} className="btn-primary">
          <Search size={14} className="mr-1.5" />
          {searching ? "…" : "Buscar"}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <div key={i} className="surface p-5">
              <div className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                <BrainCircuit size={14} style={{ color: "var(--text-tertiary)" }} />
                {r.title || r.source_type || "Trecho"}
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs" style={{ color: "var(--text-tertiary)" }}>
                <span>{r.source_type || "—"}</span>
                <span>·</span>
                <span>similaridade {Number(r.similarity || 0).toFixed(3)}</span>
              </div>
              <div className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {String(r.chunk_text || "").replace(/\n+/g, " ").slice(0, 280)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, hint, loading }: { label: string; value: number | string; hint?: string; loading?: boolean }) {
  return (
    <div className="surface p-4">
      <div className="label-section mb-1">{label}</div>
      {loading ? (
        <div className="h-6 w-12 animate-pulse rounded bg-[var(--surface-subtle)]" />
      ) : (
        <div className="text-xl font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>{value}</div>
      )}
      {hint && !loading && <div className="mt-1 text-xs" style={{ color: "var(--text-tertiary)" }}>{hint}</div>}
    </div>
  );
}
