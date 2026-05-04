"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const mdClass =
  "text-sm leading-relaxed text-ink " +
  "[&_h1]:mb-2 [&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-medium " +
  "[&_p]:my-2 [&_p:first-child]:mt-0 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5 " +
  "[&_a]:text-link [&_a]:underline " +
  "[&_code]:rounded [&_code]:bg-surface-soft [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[13px] " +
  "[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-surface-soft [&_pre]:p-3 [&_pre]:text-[13px] " +
  "[&_blockquote]:border-l-2 [&_blockquote]:border-hairline [&_blockquote]:pl-3 [&_blockquote]:text-ink-muted-48 " +
  "[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs " +
  "[&_th]:border [&_th]:border-hairline [&_th]:bg-surface-soft [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-medium " +
  "[&_td]:border [&_td]:border-hairline [&_td]:px-2 [&_td]:py-1.5 " +
  "[&_hr]:my-4 [&_hr]:border-hairline";

export function AgentMarkdown({ content }: { content: string }) {
  if (!content?.trim()) {
    return null;
  }
  return (
    <div className={cn("overflow-x-auto", mdClass)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
