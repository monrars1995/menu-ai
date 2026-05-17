"use client";

import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-5 flex flex-col gap-2.5 sm:mb-6 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold leading-tight text-ink sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1 text-sm leading-5 text-ink-muted-48">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 self-start pt-0.5 sm:self-auto">{actions}</div>}
    </div>
  );
}
