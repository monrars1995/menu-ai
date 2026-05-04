import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(date));
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function statusBadge(status: string): { label: string; variant: string } {
  const map: Record<string, { label: string; variant: string }> = {
    rascunho: { label: "Rascunho", variant: "secondary" },
    em_revisao: { label: "Em Revisão", variant: "warning" },
    aguardando_aprovacao: { label: "Aguardando Aprovação", variant: "warning" },
    aprovado: { label: "Aprovado", variant: "success" },
    publicado: { label: "Publicado", variant: "default" },
    arquivado: { label: "Arquivado", variant: "muted" },
    iniciando: { label: "Iniciando", variant: "secondary" },
    executando: { label: "Executando", variant: "default" },
    concluido: { label: "Concluído", variant: "success" },
    erro: { label: "Erro", variant: "destructive" },
  };
  return map[status] || { label: status, variant: "secondary" };
}
