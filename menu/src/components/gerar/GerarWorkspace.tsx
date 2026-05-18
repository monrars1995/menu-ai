"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type GerarWorkspaceProps = {
  topBar: ReactNode;
  children: ReactNode;
  input?: ReactNode;
  className?: string;
};

export function GerarWorkspace({ topBar, children, input, className }: GerarWorkspaceProps) {
  return (
    <section className={cn("flex min-h-0 flex-1 flex-col overflow-hidden", className)}>
      <div className="mx-auto mb-5 w-full max-w-5xl shrink-0">{topBar}</div>
      <div className="mx-auto relative flex min-h-0 w-full max-w-5xl flex-1 flex-col overflow-hidden">
        {children}
      </div>
      {input ? <div className="mx-auto w-full max-w-5xl shrink-0">{input}</div> : null}
    </section>
  );
}
