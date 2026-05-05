"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Send, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { MealSelector } from "@/components/meal-selector";
import type { ChatPhase } from "@/components/chat/useChatGenerator";

const stickyInputShell =
  "sticky bottom-0 z-10 border-t border-hairline bg-white px-3 py-3 sm:px-4 sm:py-4 pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))] sm:pb-[calc(1rem+env(safe-area-inset-bottom,0px))]";

export interface MessageInputProps {
  phase: ChatPhase;
  contratos?: Array<{ id: string; nome: string }>;
  loadingContratos?: boolean;
  onSelectContrato?: (id: string) => void;
  onGoToUpload?: () => void;
  diasValue?: number;
  onSetDias?: (v: number) => void;
  refeicoesValue?: string[];
  onSetRefeicoes?: (v: string[]) => void;
  custoValue?: string;
  onSetCustoAlvo?: (v: string) => void;
  onSkipCost?: () => void;
  restricoesValue?: string;
  onSetRestricoes?: (v: string) => void;
  onSkipRestrictions?: () => void;
  onInlineUpload?: (file: File) => void;
  onSendMessage?: (text: string) => void;
}

export function MessageInput(props: MessageInputProps) {
  const { phase } = props;
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const [diasDraft, setDiasDraft] = useState(String(props.diasValue ?? 5));
  const [custoDraft, setCustoDraft] = useState(props.custoValue ?? "");
  const [restricoesDraft, setRestricoesDraft] = useState(props.restricoesValue ?? "");
  const [chatDraft, setChatDraft] = useState("");

  const prevPhase = useRef<ChatPhase>(phase);
  useEffect(() => {
    if (phase !== prevPhase.current) {
      if (phase === "config-days") setDiasDraft(String(props.diasValue ?? 5));
      else if (phase === "config-cost") setCustoDraft(props.custoValue ?? "");
      else if (phase === "config-restrictions") setRestricoesDraft(props.restricoesValue ?? "");
      prevPhase.current = phase;
    }
  }, [phase, props.diasValue, props.custoValue, props.restricoesValue]);

  // Welcome / analysis — contract selection + upload
  if (phase === "welcome" || phase === "analysis") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <ContractDropdown
              contratos={props.contratos}
              loadingContratos={props.loadingContratos}
              dropdownOpen={dropdownOpen}
              setDropdownOpen={setDropdownOpen}
              onSelect={(id) => {
                props.onSelectContrato?.(id);
                setDropdownOpen(false);
              }}
            />
            <UploadButton onUpload={props.onInlineUpload} />
          </div>
        </div>
      </div>
    );
  }

  // Uploading — loading state
  if (phase === "uploading") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs text-ink-muted-48">Enviando arquivo...</p>
        </div>
      </div>
    );
  }

  // Days — numeric input
  if (phase === "config-days") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={30}
                value={diasDraft}
                onChange={(e) => setDiasDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    const v = parseInt(diasDraft) || 5;
                    props.onSetDias?.(Math.min(30, Math.max(1, v)));
                  }
                }}
                className="w-24 rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
              <span className="text-xs text-ink-muted-48">1–30 dias</span>
            </div>
            <button
              onClick={() => {
                const v = parseInt(diasDraft) || 5;
                props.onSetDias?.(Math.min(30, Math.max(1, v)));
              }}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border sm:ml-auto sm:w-auto"
            >
              <Send size={14} />
              Confirmar
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Meals — inline MealSelector
  if (phase === "config-meals") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="max-h-[min(50vh,22rem)] overflow-y-auto sm:max-h-none">
            <MealSelector
              selected={props.refeicoesValue ?? []}
              onChange={(v) => {
                if (v.length > 0) props.onSetRefeicoes?.(v);
              }}
            />
          </div>
        </div>
      </div>
    );
  }

  // Cost — monetary with skip
  if (phase === "config-cost") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-ink-muted-48">R$</span>
              <input
                type="number"
                step="0.01"
                min={0}
                value={custoDraft}
                onChange={(e) => setCustoDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (custoDraft.trim()) props.onSetCustoAlvo?.(custoDraft.trim());
                    else props.onSkipCost?.();
                  }
                }}
                placeholder="Opcional"
                className="min-w-0 flex-1 rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)] sm:w-32 sm:flex-none"
              />
            </div>
            <div className="flex w-full gap-2 sm:ml-auto sm:w-auto">
              <button
                onClick={() => {
                  if (custoDraft.trim()) props.onSetCustoAlvo?.(custoDraft.trim());
                  else props.onSkipCost?.();
                }}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border sm:flex-initial"
              >
                <Send size={14} />
                Confirmar
              </button>
              <button
                onClick={props.onSkipCost}
                className="shrink-0 rounded-md px-3 py-2 text-sm text-link hover:underline"
              >
                Pular
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Restrictions — textarea with skip
  if (phase === "config-restrictions") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <textarea
              value={restricoesDraft}
              onChange={(e) => setRestricoesDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (restricoesDraft.trim()) props.onSetRestricoes?.(restricoesDraft.trim());
                  else props.onSkipRestrictions?.();
                }
              }}
              placeholder="Ex: sem gluten, sem lactose, vegano..."
              rows={2}
              className="min-h-[4.5rem] w-full resize-none rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)] sm:min-h-0 sm:flex-1"
            />
            <div className="flex shrink-0 justify-end gap-2 sm:flex-col sm:justify-start">
              <button
                onClick={() => {
                  if (restricoesDraft.trim()) props.onSetRestricoes?.(restricoesDraft.trim());
                  else props.onSkipRestrictions?.();
                }}
                className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border"
              >
                <Send size={14} />
              </button>
              <button
                onClick={props.onSkipRestrictions}
                className="rounded-md px-3 py-2 text-sm text-link hover:underline sm:pb-2"
              >
                Pular
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Generating / result / error / hitl-confirm — Free chat input
  if (phase === "generating" || phase === "result" || phase === "error" || phase === "hitl-confirm") {
    return (
      <div className={stickyInputShell}>
        <div className="mx-auto max-w-2xl">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <textarea
              value={chatDraft}
              onChange={(e) => setChatDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (chatDraft.trim()) {
                    props.onSendMessage?.(chatDraft.trim());
                    setChatDraft("");
                  }
                }
              }}
              placeholder={phase === "hitl-confirm" ? "Ajuste os dados antes de confirmar..." : "Envie uma instrução ou refinamento..."}
              rows={1}
              className="min-h-[2.5rem] max-h-[8rem] w-full resize-none rounded-md border border-hairline bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)] sm:flex-1"
            />
            <div className="flex shrink-0 justify-end gap-2">
              <button
                onClick={() => {
                  if (chatDraft.trim()) {
                    props.onSendMessage?.(chatDraft.trim());
                    setChatDraft("");
                  }
                }}
                className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
          {phase === "generating" && (
            <p className="mt-2 text-center text-xs text-ink-muted-48">Geração em andamento...</p>
          )}
        </div>
      </div>
    );
  }

  // Fallback
  return (
    <div className="sticky bottom-0 z-10 border-t border-hairline bg-white px-4 py-4">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-xs text-ink-muted-48">Confira os parametros e clique em Gerar Cardapio.</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Contract dropdown
// ---------------------------------------------------------------------------

function ContractDropdown({
  contratos,
  loadingContratos,
  dropdownOpen,
  setDropdownOpen,
  onSelect,
}: {
  contratos?: Array<{ id: string; nome: string }>;
  loadingContratos?: boolean;
  dropdownOpen: boolean;
  setDropdownOpen: (v: boolean) => void;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="relative">
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className={cn(
          "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-all",
          dropdownOpen
            ? "border-ink bg-ink/5 text-ink ring-2 ring-ink/15"
            : "border-hairline bg-white text-ink hover:bg-surface-soft hover:shadow-sm"
        )}
      >
        <FileText size={14} />
        Selecionar Contrato
      </button>
      {dropdownOpen && (
        <div className="absolute bottom-full left-0 mb-2 max-h-52 w-72 overflow-y-auto rounded-xl border border-hairline bg-white shadow-xl shadow-black/10">
          {loadingContratos ? (
            <div className="flex items-center gap-2 p-4">
              <Loader2 size={14} className="animate-spin text-ink" />
              <p className="text-xs text-ink-muted-48">Carregando contratos...</p>
            </div>
          ) : contratos && contratos.length === 0 ? (
            <p className="p-4 text-xs text-ink-muted-48">Nenhum contrato encontrado</p>
          ) : (
            <div className="py-1">
              {contratos?.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  className="block w-full px-4 py-2.5 text-left text-sm text-ink hover:bg-surface-soft"
                >
                  {c.nome}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function UploadButton({ onUpload }: { onUpload?: (file: File) => void }) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <button
        onClick={() => fileRef.current?.click()}
        className="flex items-center gap-2 rounded-lg border border-hairline bg-white px-4 py-2 text-sm font-medium text-ink transition-all hover:bg-surface-soft hover:shadow-sm"
      >
        <Upload size={14} />
        Upload PDF
      </button>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload?.(f);
          e.target.value = "";
        }}
      />
    </>
  );
}
