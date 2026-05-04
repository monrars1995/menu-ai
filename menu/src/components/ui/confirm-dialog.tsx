"use client";

import { Modal } from "./modal";
import { Button } from "./button";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
}

export function ConfirmDialog({ open, onClose, onConfirm, title, message, confirmLabel = "Confirmar", danger = false, loading = false }: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <p className="text-sm text-ink-muted-80">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button variant={danger ? "danger" : "primary"} size="sm" onClick={onConfirm} disabled={loading}>
          {loading ? "Processando…" : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}