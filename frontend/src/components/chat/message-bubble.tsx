"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Sparkles, Copy, Check, ArrowUpRight } from "lucide-react";
import { toast } from "sonner";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Markdown } from "./markdown";
import { EvidencePanels } from "./evidence-panels";
import { ConfirmationCard } from "./confirmation-card";

export function MessageBubble({
  message,
  isLast,
  onConfirm,
  onCancel,
  busy,
}: {
  message: ChatMessage;
  isLast: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  const [copied, setCopied] = React.useState(false);
  const isUser = message.role === "user";

  function copy() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 1500);
  }

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const meta = message.meta;
  const showConfirm = isLast && meta?.pending_action && !meta?.committed;

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="group flex gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
<div className="flex items-center gap-2">
           <span className="text-sm font-medium">ParcelPilot</span>
           {!message.streaming && (
             <button
               onClick={copy}
               className="ml-auto opacity-0 transition-opacity group-hover:opacity-100"
               aria-label="Copy"
             >
               {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground" />}
             </button>
           )}
         </div>

        <div className="mt-1">
          {message.content ? (
            <Markdown content={message.content} />
          ) : (
            <span className="inline-flex gap-1">
              <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted-foreground" />
              <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted-foreground [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted-foreground [animation-delay:300ms]" />
            </span>
          )}
          {message.streaming && message.content && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse-soft bg-primary align-middle" />}
        </div>

        {meta?.escalation?.recommended && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">
            <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div>
              <span className="font-medium text-destructive">Escalation recommended</span>
              <p className="text-muted-foreground">{meta.escalation.reason}</p>
            </div>
          </div>
        )}

        {showConfirm && meta?.pending_action && (
          <ConfirmationCard action={meta.pending_action} onConfirm={onConfirm} onCancel={onCancel} disabled={busy} />
        )}

        {meta && <EvidencePanels meta={meta} />}
      </div>
    </motion.div>
  );
}
