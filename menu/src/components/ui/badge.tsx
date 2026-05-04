"use client";

import { cn } from "@/lib/utils";
import { statusBadge } from "@/lib/utils";

interface BadgeProps {
  status: string;
  className?: string;
}

const variantMap: Record<string, string> = {
  success: "bg-success/10 text-success border border-success-border/30",
  warning: "bg-amber-50 text-amber-800 border border-amber-200",
  destructive: "bg-red-50 text-red-700 border border-red-200",
  default: "bg-primary/8 text-primary border border-primary/20",
  secondary: "bg-surface-soft text-ink-muted-80 border border-hairline",
  muted: "bg-surface-soft text-ink-muted-48 border border-hairline",
};

export function StatusBadge({ status, className }: BadgeProps) {
  const { label, variant } = statusBadge(status);
  return (
    <span className={cn("inline-flex rounded-md px-2 py-0.5 text-[10px] font-semibold", variantMap[variant] || variantMap.secondary, className)}>
      {label}
    </span>
  );
}

type SimpleBadgeVariant = "info" | "success" | "warning" | "danger" | "neutral";

interface SimpleBadgeProps {
  variant?: SimpleBadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const simpleVariantMap: Record<SimpleBadgeVariant, string> = {
  info: "bg-blue-50 text-info border border-info-border/30",
  success: "bg-success/10 text-success border border-success-border/30",
  warning: "bg-amber-50 text-amber-800 border border-amber-200",
  danger: "bg-red-50 text-red-700 border border-red-200",
  neutral: "bg-surface-soft text-ink-muted-48 border border-hairline",
};

export function Badge({ variant = "neutral", children, className }: SimpleBadgeProps) {
  return (
    <span className={cn("inline-flex rounded-md px-2 py-0.5 text-[10px] font-semibold", simpleVariantMap[variant], className)}>
      {children}
    </span>
  );
}
