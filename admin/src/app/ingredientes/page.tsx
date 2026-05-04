"use client";

import ListPage from "@/components/ListPage";

interface Ingrediente {
  nome: string;
  categoria?: string;
  custo_unitario?: number;
  fator_correcao?: number;
  ativo: boolean;
}

const columns = [
  { key: "nome" as const, label: "Nome" },
  { key: "categoria" as const, label: "Categoria" },
  { key: "fator_correcao" as const, label: "F.C.", fmt: (v: unknown) => v != null ? Number(v).toFixed(2) : "—" },
  { key: "custo_unitario" as const, label: "Custo/kg", fmt: (v: unknown) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—") },
  { key: "ativo" as const, label: "Ativo" },
];

export default function IngredientesPage() {
  return (
    <ListPage<Ingrediente>
      title="Ingredientes"
      subtitle="Insumos com custo real e fator de correcao"
      endpoint="/api/ingredientes/"
      columns={columns}
    />
  );
}
