"use client";

import ListPage from "@/components/ListPage";

interface Ficha {
  nome: string;
  categoria?: string;
  custo_porcao?: number;
  peso_porcao_g?: number;
  ativo: boolean;
}

const columns = [
  { key: "nome" as const, label: "Nome" },
  { key: "categoria" as const, label: "Categoria" },
  { key: "peso_porcao_g" as const, label: "Peso (g)", fmt: (v: unknown) => v != null ? `${Number(v).toFixed(0)}g` : "—" },
  { key: "custo_porcao" as const, label: "Custo/porção", fmt: (v: unknown) => (v != null ? `R$ ${Number(v).toFixed(2)}` : "—") },
  { key: "ativo" as const, label: "Ativo" },
];

export default function FichasPage() {
  return (
    <ListPage<Ficha>
      title="Fichas T\xc3\xa9cnicas"
      subtitle="Receitas com custo e composicao nutricional"
      endpoint="/api/fichas-tecnicas/"
      columns={columns}
    />
  );
}
