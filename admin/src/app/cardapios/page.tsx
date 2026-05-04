"use client";

import ListPage from "@/components/ListPage";

interface Cardapio {
  nome: string;
  status?: string;
  num_dias?: number;
  custo_medio_dia?: number;
  created_at?: string;
}

const statusFmt = (v: unknown) => {
  const s = String(v || "");
  const map: Record<string, string> = {
    rascunho: "Rascunho",
    em_revisao: "Em revisão",
    aprovado: "Aprovado",
    publicado: "Publicado",
    arquivado: "Arquivado",
  };
  return map[s] || s || "—";
};

const columns = [
  { key: "nome" as const, label: "Nome" },
  { key: "status" as const, label: "Status", fmt: statusFmt },
  { key: "num_dias" as const, label: "Dias" },
  { key: "custo_medio_dia" as const, label: "Custo/dia", fmt: (v: unknown) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—") },
  { key: "created_at" as const, label: "Criado em", fmt: (v: unknown) => v ? new Date(String(v)).toLocaleDateString("pt-BR") : "—" },
];

export default function CardapiosPage() {
  return (
    <ListPage<Cardapio>
      title="Cardápios"
      subtitle="Cardápios gerados e em workflow"
      endpoint="/api/cardapios/"
      columns={columns}
    />
  );
}
