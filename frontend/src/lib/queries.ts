"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./api";
import type { Conversation, SystemInfo, User } from "./types";

export function useSystemInfo() {
  return useQuery({ queryKey: ["system"], queryFn: () => apiFetch<SystemInfo>("/system/info") });
}

export function useDemoUsers() {
  return useQuery({ queryKey: ["demo-users"], queryFn: () => apiFetch<User[]>("/auth/users") });
}

export function useConversations() {
  return useQuery({ queryKey: ["conversations"], queryFn: () => apiFetch<Conversation[]>("/conversations") });
}

export function useMessages(conversationId: number | null) {
  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => apiFetch<any[]>(`/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
  });
}

export function usePinConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, pinned }: { id: number; pinned: boolean }) =>
      apiFetch(`/conversations/${id}/pin`, { method: "PATCH", body: JSON.stringify({ pinned }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => apiFetch<any>("/ops/dashboard") });
}

export function useAnalytics() {
  return useQuery({ queryKey: ["analytics"], queryFn: () => apiFetch<any>("/analytics") });
}

export function useTickets() {
  return useQuery({ queryKey: ["tickets"], queryFn: () => apiFetch<any[]>("/tickets") });
}

export function useTicket(code: string | null) {
  return useQuery({
    queryKey: ["ticket", code],
    queryFn: () => apiFetch<any>(`/tickets/${code}`),
    enabled: !!code,
  });
}

export function useOrders() {
  return useQuery({ queryKey: ["orders"], queryFn: () => apiFetch<any[]>("/orders") });
}

export function useAccounts() {
  return useQuery({ queryKey: ["accounts"], queryFn: () => apiFetch<any[]>("/accounts") });
}

export function useDocuments() {
  return useQuery({ queryKey: ["documents"], queryFn: () => apiFetch<any[]>("/knowledge/documents") });
}

export function useAuditLog() {
  return useQuery({ queryKey: ["audit"], queryFn: () => apiFetch<any[]>("/audit") });
}

export function useToolExecutions() {
  return useQuery({ queryKey: ["tool-exec"], queryFn: () => apiFetch<any[]>("/tools/executions") });
}
