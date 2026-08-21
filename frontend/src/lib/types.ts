// Shared types mirroring the backend API contracts.

export type Role = "customer" | "support" | "manager" | "admin";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  account_code?: string | null;
  account_name?: string | null;
}

export interface Citation {
  marker: string;
  document_code: string;
  title: string;
  heading: string;
  source_type: string;
  status: string;
  authority_rank: number;
  source_file?: string | null;
  relevance: number;
}

export interface ConflictSource {
  label: string;
  value: string;
  authority_rank: number;
  status: string;
}

export interface Conflict {
  topic: string;
  description: string;
  sources: ConflictSource[];
  resolution: string;
  resolved_value?: string | null;
  recommended_action?: string | null;
  requires_escalation: boolean;
}

export interface TraceEvent {
  node: string;
  label: string;
  detail: string;
}

export interface ToolCall {
  tool: string;
  ok: boolean;
  summary: string;
  latency_ms: number;
  requires_confirmation: boolean;
  error?: string | null;
}

export interface PendingAction {
  tool: string;
  human: string;
  consequences: string[];
  params: Record<string, unknown>;
}

export interface ChatMeta {
  intent?: string;
  summary?: string;
  recommendation?: string;
  confidence: number;
  confidence_band: "LOW" | "MEDIUM" | "HIGH";
  citations: Citation[];
  conflicts: Conflict[];
  trace: TraceEvent[];
  tool_calls: ToolCall[];
  evidence: { kind: string; label: string; detail: string }[];
  pending_action?: PendingAction | null;
  escalation?: { recommended: boolean; severity: string; reason: string } | null;
  committed?: { ok: boolean; summary: string } | null;
}

export interface ChatMessage {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  meta?: ChatMeta;
  created_at?: string;
  streaming?: boolean;
}

export interface Conversation {
  id: number;
  title: string;
  pinned: boolean;
  updated_at: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface SystemInfo {
  llm_mode: "mock" | "live";
  llm_model: string | null;
  embeddings: string;
  reference_time: string;
  role: Role;
}
