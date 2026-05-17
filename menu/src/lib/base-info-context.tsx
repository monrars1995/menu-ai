"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

type BaseInfoStatus = "loading" | "ready" | "error";

interface BaseInfoData {
  totalFichas: number;
  totalIngredientes: number;
  categorias: Record<string, number>;
  scope?: string;
  empresaId?: string | null;
}

interface BaseInfoContextValue {
  status: BaseInfoStatus;
  data: BaseInfoData;
  title: string;
  message: string;
  refresh: () => Promise<void>;
}

const BaseInfoContext = createContext<BaseInfoContextValue | null>(null);

const EMPTY_DATA: BaseInfoData = {
  totalFichas: 0,
  totalIngredientes: 0,
  categorias: {},
  scope: undefined,
  empresaId: null,
};

function buildTitle(data: BaseInfoData, status: BaseInfoStatus): string {
  if (status === "loading") return "Carregando base...";
  if (status === "error") return "Base indisponível";
  const topCats = Object.entries(data.categorias || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name, count]) => `${name}: ${count}`)
    .join(" • ");
  const scopeLabel = data.scope ? `Escopo: ${data.scope}` : "Escopo: empresa";
  return [
    `Fichas: ${data.totalFichas}`,
    `Ingredientes: ${data.totalIngredientes}`,
    scopeLabel,
    topCats || "Sem categorias",
  ].join("\n");
}

function buildMessage(data: BaseInfoData, status: BaseInfoStatus): string {
  if (status === "loading") return "Carregando base...";
  if (status === "error") return "Base indisponível";
  return `Base: ${data.totalFichas} fichas • ${data.totalIngredientes} ingredientes`;
}

export function BaseInfoProvider({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const [status, setStatus] = useState<BaseInfoStatus>("loading");
  const [data, setData] = useState<BaseInfoData>(EMPTY_DATA);

  async function refresh() {
    if (loading || !user) return;
    setStatus("loading");
    try {
      const r = await api.info();
      if (r?.error || r?.db_status !== "conectado") {
        setData(EMPTY_DATA);
        setStatus("error");
        return;
      }
      setData({
        totalFichas: Number(r?.total_fichas ?? 0),
        totalIngredientes: Number(r?.total_ingredientes ?? 0),
        categorias: (r?.categorias ?? {}) as Record<string, number>,
        scope: r?.scope,
        empresaId: r?.empresa_id ?? null,
      });
      setStatus("ready");
    } catch {
      setData(EMPTY_DATA);
      setStatus("error");
    }
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setData(EMPTY_DATA);
      setStatus("error");
      return;
    }
    refresh();
  }, [loading, user?.id]);

  const value = useMemo<BaseInfoContextValue>(() => {
    return {
      status,
      data,
      title: buildTitle(data, status),
      message: buildMessage(data, status),
      refresh,
    };
  }, [status, data]);

  return <BaseInfoContext.Provider value={value}>{children}</BaseInfoContext.Provider>;
}

export function useBaseInfo() {
  const ctx = useContext(BaseInfoContext);
  if (!ctx) throw new Error("useBaseInfo must be inside BaseInfoProvider");
  return ctx;
}

