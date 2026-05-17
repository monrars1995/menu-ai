"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { Cpu } from "lucide-react";

interface LlmModel {
  id: string;
  label?: string;
  provider?: string;
  model_string?: string;
  slug?: string;
  description?: string;
  enabled: boolean;
}

interface LlmPayload {
  provider?: string;
  default?: string;
  models: LlmModel[];
}

export default function LlmPage() {
  const { apiFetch } = useApi();
  const [payload, setPayload] = useState<LlmPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await apiFetch("/api/admin/llm-models");
    if (res.ok) {
      const data = await res.json();
      setPayload(data);
    }
    setLoading(false);
  }

  async function toggle(id: string, enabled: boolean) {
    const res = await apiFetch(`/api/admin/llm-models/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    });
    if (!res.ok) {
      alert("Não foi possível atualizar o modelo.");
      load();
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-page-title">Modelos LLM</h1>
        <p className="text-subtitle">
          {payload ? `Provedor: ${payload.provider || "—"} · Padrão: ${payload.default || "—"}` : "Carregando…"}
        </p>
      </div>

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-ink)]" />
        </div>
      ) : (
        <div className="space-y-2">
          {payload?.models.map((m) => (
            <div
              key={m.id}
              className="surface flex items-center justify-between px-5 py-3.5"
            >
              <div>
                <div className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  <Cpu size={14} style={{ color: "var(--text-tertiary)" }} />
                  {m.label || m.id}
                  {payload.default === m.id && (
                    <span className="badge badge-primary">Padrão</span>
                  )}
                  {!m.enabled && (
                    <span className="badge badge-default">Desativado</span>
                  )}
                </div>
                <div className="mt-0.5 text-xs" style={{ color: "var(--text-tertiary)" }}>
                  {m.id}{m.provider ? ` · ${m.provider}` : ""}{m.model_string ? ` · ${m.model_string}` : m.slug ? ` · ${m.slug}` : ""}
                </div>
                {m.description && <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>{m.description}</div>}
              </div>
              <ToggleSwitch checked={m.enabled} onChange={(v) => toggle(m.id, v)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div
      role="switch"
      aria-checked={checked}
      className={`toggle-track ${checked ? "checked" : ""}`}
      onClick={() => onChange(!checked)}
    >
      <div className="toggle-knob" />
    </div>
  );
}
