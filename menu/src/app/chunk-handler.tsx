"use client";

import { useEffect } from "react";

export function ChunkErrorHandler() {
  useEffect(() => {
    const handleChunkError = (e: Event) => {
      const target = e.target as HTMLElement;
      const isChunk =
        target?.tagName === "SCRIPT" &&
        (target as HTMLScriptElement)?.src?.includes("chunks/");
      if (isChunk) {
        if (sessionStorage.getItem("chunk-reload-attempted")) {
          return;
        }
        sessionStorage.setItem("chunk-reload-attempted", "true");
        window.location.reload();
      }
    };

    window.addEventListener("error", handleChunkError, true);
    return () => window.removeEventListener("error", handleChunkError, true);
  }, []);

  return null;
}
