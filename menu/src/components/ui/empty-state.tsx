"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, actionLabel, actionHref, onAction, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center", className)}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-surface-soft text-ink-muted-48">
        <Icon size={24} />
      </div>
      <p className="text-sm font-medium text-ink">{title}</p>
      {description && <p className="mt-1.5 text-xs text-ink-muted-48">{description}</p>}
      {actionLabel && actionHref && (
        <Link href={actionHref} className="mt-4 text-sm font-medium text-link hover:underline">
          {actionLabel}
        </Link>
      )}
      {actionLabel && !actionHref && onAction && (
        <button onClick={onAction} className="mt-4 text-sm font-medium text-link hover:underline">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
