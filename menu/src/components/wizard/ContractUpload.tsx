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
    <div className="flex flex-col space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-ink">Selecione o Contrato</h2>
        <p className="text-sm text-ink-muted-48 mt-1">
          Escolha um contrato existente ou envie um novo arquivo (PDF/Excel)
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Upload Card */}
        <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-hairline rounded-xl hover:border-primary hover:bg-surface-elevated transition-colors cursor-pointer group h-full min-h-[200px]">
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-surface flex items-center justify-center group-hover:bg-primary/10 transition-colors">
              <Upload className="w-6 h-6 text-ink-muted-48 group-hover:text-primary transition-colors" />
            </div>
            <div className="text-center">
              <span className="text-sm font-medium text-ink block">
                Fazer upload de arquivo
              </span>
              <span className="text-xs text-ink-muted-48">
                PDF, XLS, ou XLSX (Max 10MB)
              </span>
            </div>
          </div>
          <input
            type="file"
            className="hidden"
            accept=".pdf,.xls,.xlsx"
            onChange={handleFileChange}
          />
        </label>

        {/* Existing Contracts List */}
        <div className="flex flex-col p-4 border border-hairline rounded-xl bg-surface-elevated min-h-[200px] max-h-[300px] overflow-y-auto">
          <h3 className="text-sm font-semibold text-ink mb-3 sticky top-0 bg-surface-elevated pb-2 z-10">
            Contratos Salvos
          </h3>
          
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : contratos.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-ink-muted-48">
              <FileText className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-xs">Nenhum contrato encontrado.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {contratos.map((contrato) => (
                <button
                  key={contrato.id}
                  onClick={() => onSelect(contrato.id)}
                  className="w-full flex items-center p-3 text-left bg-white border border-hairline rounded-lg hover:border-primary hover:shadow-sm transition-all group"
                >
                  <FileText className="w-5 h-5 text-ink-muted-48 mr-3 group-hover:text-primary transition-colors" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-ink truncate">
                      {contrato.nome}
                    </p>
                    <p className="text-xs text-ink-muted-48 truncate">
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
