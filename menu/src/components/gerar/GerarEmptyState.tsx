"use client";

import { ContractUpload } from "@/components/wizard/ContractUpload";

type GerarEmptyStateProps = {
  onSelectContrato: (contratoId: string) => void;
  onUploadContrato: (file: File) => void;
};

export function GerarEmptyState({
  onSelectContrato,
  onUploadContrato,
}: GerarEmptyStateProps) {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-12rem)] w-full max-w-4xl flex-col justify-center px-3 py-8 sm:px-6">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-medium tracking-tight text-ink sm:text-4xl">
          Por onde começamos?
        </h1>
        <p className="mt-3 text-sm text-ink-muted">
          Envie um contrato ou escolha um contrato salvo para iniciar a análise.
        </p>
      </div>

      <ContractUpload onSelect={onSelectContrato} onUpload={onUploadContrato} />
    </div>
  );
}
