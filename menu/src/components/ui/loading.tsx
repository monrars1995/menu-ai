"use client";

import { cn } from "@/lib/utils";

interface SpinnerProps {
  size?: number;
  className?: string;
}

export function Spinner({ size = 20, className }: SpinnerProps) {
  return (
    <div
      className={cn("animate-spin rounded-full border-2 border-primary border-t-transparent", className)}
      style={{ width: size, height: size }}
    />
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Spinner size={28} />
    </div>
  );
}

export function InlineLoader({ text = "Carregando…" }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-muted-48">
      <Spinner size={14} />
      {text}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-ink/5", className)} />;
}

export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-24" />
        </td>
      ))}
    </tr>
  );
}