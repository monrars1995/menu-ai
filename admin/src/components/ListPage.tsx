"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/api";
import DataTable from "@/components/DataTable";
import { ArrowLeft, RotateCw } from "lucide-react";

// ============================================================
// Reusable list hook
// ============================================================

export function useList<T extends object>(endpoint: string) {
  const { apiFetch } = useApi();
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    const res = await apiFetch(`${endpoint}?skip=0&limit=200`);
    if (!res.ok) {
      setError(`Erro ${res.status}`);
      setRows([]);
    } else {
      const data = await res.json();
      setRows(Array.isArray(data) ? data : data.items || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  return { rows, loading, error, refresh: load };
}

// ============================================================
// Page wrapper
// ============================================================

interface ListPageProps<T extends object> {
  title: string;
  subtitle?: string;
  endpoint: string;
  columns: { key: keyof T | string; label: string; fmt?: (v: unknown, row: T) => string }[];
  actions?: React.ReactNode;
  emptyText?: string;
  backTo?: string;
}

export default function ListPage<T extends object>({
  title,
  subtitle,
  endpoint,
  columns,
  actions,
  emptyText,
  backTo,
}: ListPageProps<T>) {
  const router = useRouter();
  const { rows, loading, error, refresh } = useList<T>(endpoint);

  return (
    <div className="animate-fade-in">
      {/* Page header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          {backTo && (
            <button
              onClick={() => router.push(backTo)}
              className="btn-ghost -ml-2 mb-1"
            >
              <ArrowLeft size={14} />
              Voltar
            </button>
          )}
          <h1 className="text-page-title">{title}</h1>
          {subtitle && <p className="text-subtitle">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <button onClick={refresh} className="btn-secondary text-xs" disabled={loading}>
            <RotateCw size={14} className={loading ? "animate-spin" : ""} />
            Atualizar
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-primary)]" />
        </div>
      ) : (
        <DataTable columns={columns} rows={rows} emptyText={emptyText} />
      )}
    </div>
  );
}
