"use client";

import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:mb-7 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-[30px] font-medium tracking-tight text-ink sm:text-[34px]">{title}</h1>
        {description && <p className="mt-1.5 text-sm text-ink-muted-48">{description}</p>}
      </div>
      {actions && <div className="flex gap-2 self-start sm:self-auto">{actions}</div>}
    </div>
  );
}
