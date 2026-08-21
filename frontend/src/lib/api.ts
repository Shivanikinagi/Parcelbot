"use client";

import { getToken } from "./auth-store";
import type { ChatMeta } from "./types";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

const BASE = "/api";

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let payload: any = null;
    try {
      payload = await res.json();
    } catch {
      /* ignore */
    }
    const err = payload?.error ?? {};
    throw new ApiError(err.message ?? res.statusText, err.code ?? "error", res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- SSE streaming chat ----------------------------------------------------
export interface StreamHandlers {
  onStart?: (conversationId: number) => void;
  onMeta?: (meta: ChatMeta, conversationId: number) => void;
  onToken?: (chunk: string) => void;
  onDone?: (messageId: number, conversationId: number) => void;
  onError?: (message: string) => void;
}

export interface StreamPayload {
  message: string;
  conversation_id?: number | null;
  confirm_action?: Record<string, unknown> | null;
}

export async function streamChat(payload: StreamPayload, handlers: StreamHandlers, signal?: AbortSignal): Promise<void> {
  const token = getToken();
  const res = await fetch(`${BASE}/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError?.(`Request failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      let event: any;
      try {
        event = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      switch (event.type) {
        case "start":
          handlers.onStart?.(event.conversation_id);
          break;
        case "meta":
          handlers.onMeta?.(event.meta, event.conversation_id);
          break;
        case "token":
          handlers.onToken?.(event.content);
          break;
        case "done":
          handlers.onDone?.(event.message_id, event.conversation_id);
          break;
        case "error":
          handlers.onError?.(event.message);
          break;
      }
    }
  }
}
