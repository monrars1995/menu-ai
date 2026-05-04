"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
}

export function Table<T>({ columns, data, keyExtractor, onRowClick, emptyMessage = "Nenhum dado encontrado", className }: TableProps<T>) {
  return (
    <div className={cn("overflow-x-auto rounded-lg border border-hairline bg-white", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-hairline bg-surface-soft text-left">
            {columns.map((col) => (
              <th key={col.key} className={cn("px-4 py-3 text-xs font-medium text-ink-muted-48", col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-hairline">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-16 text-center text-sm text-ink-muted-48">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={keyExtractor(row)}
                onClick={() => onRowClick?.(row)}
                className={cn("transition-colors", onRowClick && "cursor-pointer hover:bg-surface-soft")}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-4 py-3 text-ink", col.className)}>
                    {col.render ? col.render(row) : (row as any)[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
