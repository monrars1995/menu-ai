import { useState, useEffect } from "react";
import { Upload, FileText, Loader2 } from "lucide-react";
import api from "@/lib/api";
import type { Contrato } from "@/lib/types";

interface ContractUploadProps {
  onSelect: (contratoId: string) => void;
  onUpload: (file: File) => void;
}

export function ContractUpload({ onSelect, onUpload }: ContractUploadProps) {
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.contratos
      .list()
      .then((res) => {
        setContratos(res.items || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load contratos", err);
        setLoading(false);
      });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div className="w-full space-y-5">
      <div className="mx-auto flex max-w-3xl items-center gap-3 rounded-xl border border-hairline bg-white p-3">
        <label
          className="inline-flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-md bg-surface-soft text-ink-muted-48 transition-colors hover:text-ink"
          title="Enviar contrato"
        >
          <Upload className="h-4 w-4" />
          <input
            type="file"
            className="hidden"
            accept=".pdf,.xls,.xlsx"
            onChange={handleFileChange}
          />
        </label>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ink">Enviar contrato</p>
          <p className="text-xs text-ink-muted-48">PDF/XLSX para análise automática</p>
        </div>
      </div>

      <div className="mx-auto max-w-3xl">
        <div className="mb-2 flex items-center gap-2 px-1">
          <FileText className="h-4 w-4 text-ink-muted-48" />
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted-48">Contratos salvos</p>
        </div>
        <div className="max-h-64 overflow-y-auto rounded-xl border border-hairline bg-white p-2">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-ink-muted-48">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              Carregando contratos...
            </div>
          ) : contratos.length === 0 ? (
            <div className="py-8 text-center text-sm text-ink-muted-48">
              Nenhum contrato salvo.
            </div>
          ) : (
            <div className="grid gap-1 sm:grid-cols-2">
              {contratos.map((contrato) => (
                <button
                  key={contrato.id}
                  onClick={() => onSelect(contrato.id)}
                  className="flex min-w-0 items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border"
                >
                  <FileText className="h-4 w-4 shrink-0 text-ink-muted-48" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{contrato.nome}</p>
                    <p className="truncate text-xs text-ink-muted-48">
                      {new Date(contrato.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
