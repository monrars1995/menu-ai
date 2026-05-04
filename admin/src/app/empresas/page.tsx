"use client";

import ListPage from "@/components/ListPage";

interface Empresa {
  nome: string;
  segmento?: string;
  ativo: boolean;
  id: string;
  num_comensais?: number;
}

const columns = [
  { key: "nome" as const, label: "Nome" },
  { key: "segmento" as const, label: "Segmento" },
  { key: "num_comensais" as const, label: "Comensais/dia" },
  { key: "ativo" as const, label: "Ativo" },
  { key: "id" as const, label: "ID", fmt: (v: unknown) => String(v).slice(0, 8) + "…" },
];

export default function EmpresasPage() {
  return (
    <ListPage<Empresa>
      title="Empresas"
      subtitle="Empresas e clientes contratantes"
      endpoint="/api/empresas/"
      columns={columns}
    />
  );
}
