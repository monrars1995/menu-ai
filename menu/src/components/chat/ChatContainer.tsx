"use client";

import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { Upload } from "lucide-react";

interface ChatContainerProps {
  children: React.ReactNode;
  className?: string;
  onFileDrop?: (file: File) => void;
}

export function ChatContainer({ children, className, onFileDrop }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [children]);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }

  function handleDragEnter(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext && ["pdf", "xlsx", "xls"].includes(ext)) {
        onFileDrop?.(file);
      }
    }
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "mx-auto w-full max-w-2xl relative",
        "flex flex-1 flex-col gap-8 overflow-y-auto scroll-smooth px-3 py-6 sm:px-4 sm:py-8",
        className
      )}
    >
      {dragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border-2 border-dashed border-info-border/50 bg-surface-soft/90 backdrop-blur-sm">
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-info/10">
              <Upload size={24} className="text-info" />
            </div>
            <p className="text-sm font-medium text-ink">Solte o PDF do contrato aqui</p>
          </div>
        </div>
      )}
      {children}
      <div ref={bottomRef} className="h-px" />
    </div>
  );
}

interface AgentAvatarProps {
  className?: string;
}

export function AgentAvatar({ className }: AgentAvatarProps) {
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-dark",
        className
      )}
    >
      <img src="/isotipo.svg" alt="" className="h-5 w-5" aria-hidden />
    </div>
  );
}

interface UserAvatarProps {
  className?: string;
}

export function UserAvatar({ className }: UserAvatarProps) {
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-strong",
        className
      )}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-ink-muted-48"
      >
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>
  );
}
