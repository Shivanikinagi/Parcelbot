"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { streamChat } from "@/lib/api";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";
import type { ChatMessage, ChatMeta } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Composer } from "@/components/chat/composer";
import { MessageBubble } from "@/components/chat/message-bubble";

const SUGGESTIONS_CUSTOMER = [
  "Can I cancel ORD-1001?",
  "What's the SLA on my open ticket?",
  "Am I eligible for a service credit on my failed pickup?",
];
const SUGGESTIONS_INTERNAL = [
  "What is the SLA on TKT-501 and is it breached?",
  "Triage TKT-505 and recommend next steps",
  "Escalate TKT-501",
  "Why is bulk upload failing for LumenWorks?",
];

export default function ChatPage() {
  return (
    <React.Suspense fallback={null}>
      <ChatInner />
    </React.Suspense>
  );
}

function ChatInner() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const params = useSearchParams();
  const initialConv = params.get("c");

  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = React.useState<number | null>(
    initialConv ? Number(initialConv) : null,
  );
  const [busy, setBusy] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  const isInternal = ["support", "manager", "admin"].includes(user?.role ?? "");
  const suggestions = messages.length === 0 ? (isInternal ? SUGGESTIONS_INTERNAL : SUGGESTIONS_CUSTOMER) : [];

  React.useEffect(() => {
    if (!initialConv) return;
    apiFetch<any[]>(`/conversations/${initialConv}/messages`)
      .then((rows) =>
        setMessages(
          rows.map((r) => ({ id: r.id, role: r.role, content: r.content, meta: r.meta, created_at: r.created_at })),
        ),
      )
      .catch(() => toast.error("Could not load that conversation"));
  }, [initialConv]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function patchLastAssistant(fn: (m: ChatMessage) => ChatMessage) {
    setMessages((prev) => {
      const copy = [...prev];
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === "assistant") {
          copy[i] = fn(copy[i]);
          break;
        }
      }
      return copy;
    });
  }

  async function send(text: string, confirmAction?: Record<string, unknown> | null) {
    if (busy) return;
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: text },
      { id: `a-${Date.now()}`, role: "assistant", content: "", streaming: true },
    ]);

    try {
      await streamChat(
        { message: text, conversation_id: conversationId, confirm_action: confirmAction ?? null },
        {
          onStart: (cid) => setConversationId(cid),
          onMeta: (meta: ChatMeta) => patchLastAssistant((m) => ({ ...m, meta })),
          onToken: (chunk) => patchLastAssistant((m) => ({ ...m, content: m.content + chunk })),
          onDone: () => {
            patchLastAssistant((m) => ({ ...m, streaming: false }));
            qc.invalidateQueries({ queryKey: ["conversations"] });
            qc.invalidateQueries({ queryKey: ["dashboard"] });
            qc.invalidateQueries({ queryKey: ["audit"] });
          },
          onError: (msg) => {
            patchLastAssistant((m) => ({ ...m, streaming: false, content: m.content || `⚠️ ${msg}` }));
            toast.error(msg);
          },
        },
      );
    } catch (e: any) {
      patchLastAssistant((m) => ({ ...m, streaming: false, content: m.content || "⚠️ Connection error." }));
      toast.error(e?.message ?? "Streaming failed");
    } finally {
      setBusy(false);
    }
  }

  function confirmLast() {
    const last = [...messages].reverse().find((m) => m.role === "assistant" && m.meta?.pending_action);
    const action = last?.meta?.pending_action;
    if (!action) return;
    send("Confirm", action as unknown as Record<string, unknown>);
  }

  function cancelLast() {
    patchLastAssistant((m) => (m.meta ? { ...m, meta: { ...m.meta, pending_action: null } } : m));
    setMessages((prev) => [
      ...prev,
      { id: `a-${Date.now()}`, role: "assistant", content: "Understood — I won't make that change. Nothing was modified.", meta: undefined },
    ]);
    toast.info("Action cancelled");
  }

  function newChat() {
    setMessages([]);
    setConversationId(null);
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="flex items-center justify-between px-5 py-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="h-4 w-4 text-primary" />
          ParcelPilot
        </div>
        <Button variant="ghost" size="sm" onClick={newChat}>
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-5 pb-6">
        {messages.length === 0 ? (
          <EmptyState isInternal={isInternal} />
        ) : (
          messages.map((m, i) => (
            <MessageBubble
              key={m.id}
              message={m}
              isLast={i === messages.length - 1}
              onConfirm={confirmLast}
              onCancel={cancelLast}
              busy={busy}
            />
          ))
        )}
      </div>

      <div className="border-t border-border bg-background/80 px-5 py-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <Composer onSend={send} busy={busy} suggestions={suggestions} />
        </div>
      </div>
    </div>
  );
}

function EmptyState({ isInternal }: { isInternal: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12 text-primary">
        <Sparkles className="h-7 w-7" />
      </div>
      <h2 className="text-xl font-semibold">How can I help?</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        {isInternal
          ? "Triage tickets, compute SLAs, resolve policy conflicts, and take audited actions — every answer is cited."
          : "Ask about your orders, tickets, cancellations, and service credits. Every answer cites the policy it's based on."}
      </p>
    </div>
  );
}
