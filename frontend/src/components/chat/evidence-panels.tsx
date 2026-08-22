"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FileText, GitBranch, Wrench, CheckCircle2, XCircle, Scale, ChevronDown, ChevronUp, Search, AlertCircle, Terminal, ShieldCheck, ShieldAlert, ShieldQuestion, ExternalLink } from "lucide-react";
import type { ChatMeta, Citation } from "@/lib/types";
import { titleCase } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const SOURCE_LABEL: Record<string, string> = {
  customer_agreement: "Customer Agreement",
  policy: "Current Policy",
  sop: "SOP",
  operational_guide: "Ops Guide",
  structured_data: "Structured Data",
  historical_ticket: "Historical Ticket",
  deprecated: "Deprecated",
};

function AuthorityDot({ rank }: { rank: number }) {
  const color = rank <= 1 ? "bg-success" : rank <= 3 ? "bg-primary" : rank <= 5 ? "bg-warning" : "bg-destructive";
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} title={`Authority rank ${rank}`} />;
}

function SourceIcon({ type }: { type: string }) {
  switch (type) {
    case "customer_agreement": return <FileText className="h-3.5 w-3.5" />;
    case "policy": return <Scale className="h-3.5 w-3.5" />;
    case "sop": return <Search className="h-3.5 w-3.5" />;
    case "operational_guide": return <AlertCircle className="h-3.5 w-3.5" />;
    case "structured_data": return <Terminal className="h-3.5 w-3.5" />;
    case "historical_ticket": return <GitBranch className="h-3.5 w-3.5" />;
    default: return <FileText className="h-3.5 w-3.5" />;
  }
}

function ConfidenceIndicator({ band, score }: { band?: string; score?: number }) {
  const map: Record<string, { variant: any; icon: any; label: string }> = {
    HIGH: { variant: "success", icon: ShieldCheck, label: "High" },
    MEDIUM: { variant: "warning", icon: ShieldQuestion, label: "Medium" },
    LOW: { variant: "destructive", icon: ShieldAlert, label: "Low" },
  };
  const cfg = map[band ?? "LOW"] ?? map.LOW;
  const Icon = cfg.icon;
  return (
    <Badge variant={cfg.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {cfg.label}
      {typeof score === "number" && <span className="opacity-70">{(score * 100).toFixed(0)}%</span>}
    </Badge>
  );
}

interface DocumentSection {
  heading: string;
  content: string;
  status: string;
  authority_rank: number;
}

interface DocumentDetail {
  code: string;
  title: string;
  source_type: string;
  status: string;
  version: string;
  internal_only: boolean;
  effective_date: string | null;
  sections: DocumentSection[];
}

function SourceDocumentDialog({ target, onClose }: { target: { code: string; heading: string } | null; onClose: () => void }) {
  const { data, isFetching, isError } = useQuery({
    queryKey: ["kb-document", target?.code],
    queryFn: () => apiFetch<DocumentDetail>(`/knowledge/documents/${encodeURIComponent(target!.code)}`),
    enabled: !!target,
  });
  const highlightRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (data) highlightRef.current?.scrollIntoView({ block: "center" });
  }, [data]);

  return (
    <Dialog open={!!target} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden p-0">
        <div className="max-h-[80vh] overflow-y-auto p-6">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 pr-6">
              <FileText className="h-4 w-4 shrink-0 text-primary" />
              <span>{data?.title ?? "Loading document…"}</span>
            </DialogTitle>
            {data && (
              <DialogDescription asChild>
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <Badge variant="muted" className="text-[10px]">{data.code} · {data.version}</Badge>
                  <Badge variant="muted" className="text-[10px]">{SOURCE_LABEL[data.source_type] ?? titleCase(data.source_type)}</Badge>
                  {data.status === "deprecated" && <Badge variant="destructive" className="text-[10px]">deprecated</Badge>}
                  {data.internal_only && <Badge variant="secondary" className="text-[10px]">internal</Badge>}
                </div>
              </DialogDescription>
            )}
          </DialogHeader>

          <div className="mt-4 space-y-3">
            {isFetching && <p className="text-sm text-muted-foreground">Loading…</p>}
            {isError && <p className="text-sm text-destructive">Couldn't load this document — it may be outside your access scope.</p>}
            {data?.sections.map((s) => {
              const isCited = s.heading === target?.heading;
              return (
                <div
                  key={s.heading}
                  ref={isCited ? highlightRef : undefined}
                  className={cn(
                    "rounded-lg border p-3 transition-colors",
                    isCited ? "border-primary/50 bg-primary/5" : "border-border/60",
                  )}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-sm font-medium">{s.heading}</span>
                    {isCited && <Badge className="text-[10px]">cited</Badge>}
                    {s.status === "deprecated" && <Badge variant="destructive" className="text-[10px]">deprecated</Badge>}
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">{s.content}</p>
                </div>
              );
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function EvidencePanels({ meta }: { meta: ChatMeta }) {
  const hasSources = meta.citations?.length > 0;
  const hasConflicts = meta.conflicts?.length > 0;
  const hasTrace = meta.trace?.length > 0;
  const hasTools = meta.tool_calls?.length > 0;
  if (!hasSources && !hasConflicts && !hasTrace && !hasTools) return null;

  const [expanded, setExpanded] = React.useState(false);
  const [docTarget, setDocTarget] = React.useState<{ code: string; heading: string } | null>(null);
  const totalItems = (meta.citations?.length || 0) + (meta.conflicts?.length || 0) + (meta.trace?.length || 0) + (meta.tool_calls?.length || 0);

  const first = hasSources ? "sources" : hasConflicts ? "conflicts" : hasTrace ? "reasoning" : "tools";

  return (
    <div className="mt-3 rounded-lg border border-border bg-background/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "w-full flex items-center justify-between gap-3 p-3 text-left transition-colors hover:bg-background/80",
          expanded && "bg-background/80"
        )}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-primary/10 text-primary">
            <FileText className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-medium text-foreground">Supporting evidence</span>
          <Badge variant="secondary" className="text-[10px] h-4 px-1.5">{totalItems}</Badge>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground transition-transform" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border p-2 animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="mb-2 flex items-center gap-2">
            <ConfidenceIndicator band={meta.confidence_band} score={meta.confidence} />
          </div>
          <Tabs defaultValue={first} className="space-y-2">
            <TabsList className="flex w-full flex-wrap justify-start gap-1 bg-transparent p-0">
              {hasSources && <TabsTrigger value="sources" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><SourceIcon type="customer_agreement" />Sources ({meta.citations.length})</TabsTrigger>}
              {hasConflicts && <TabsTrigger value="conflicts" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Scale className="mr-1 h-3.5 w-3.5" />Conflicts ({meta.conflicts.length})</TabsTrigger>}
              {hasTrace && <TabsTrigger value="reasoning" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><GitBranch className="mr-1 h-3.5 w-3.5" />Reasoning</TabsTrigger>}
              {hasTools && <TabsTrigger value="tools" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Wrench className="mr-1 h-3.5 w-3.5" />Tools ({meta.tool_calls.length})</TabsTrigger>}
            </TabsList>

            {hasSources && (
              <TabsContent value="sources" className="space-y-1.5 pt-1.5">
                {meta.citations.map((c) => {
                  const viewable = c.source_type !== "structured_data";
                  return (
                    <button
                      key={c.marker + c.heading}
                      type="button"
                      disabled={!viewable}
                      onClick={() => viewable && setDocTarget({ code: c.document_code, heading: c.heading })}
                      className={cn(
                        "flex w-full items-start gap-2 rounded border border-border/50 p-2 text-left transition-colors",
                        viewable && "cursor-pointer hover:border-primary/40 hover:bg-primary/5",
                      )}
                    >
                      <span className="mt-0.5 rounded bg-primary/10 px-1 py-0.5 text-[10px] font-semibold text-primary">{c.marker}</span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium">{c.title}</div>
                        <div className="truncate text-[11px] text-muted-foreground">{c.heading}</div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <AuthorityDot rank={c.authority_rank} />
                        <Badge variant="muted" className="text-[10px]">{SOURCE_LABEL[c.source_type] ?? titleCase(c.source_type)}</Badge>
                        {viewable && <ExternalLink className="h-3 w-3 text-muted-foreground" />}
                      </div>
                    </button>
                  );
                })}
              </TabsContent>
            )}

            {hasConflicts && (
              <TabsContent value="conflicts" className="space-y-1.5 pt-1.5">
                {meta.conflicts.map((cf, i) => (
                  <div key={i} className="rounded border border-warning/40 bg-warning/5 p-2">
                    <div className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                      <AlertTriangle className="h-3.5 w-3.5 text-warning" /> {cf.topic}
                    </div>
                    <div className="space-y-0.5">
                      {cf.sources.map((s, si) => (
                        <div key={si} className="flex items-center justify-between gap-2 text-xs">
                          <span className="flex items-center gap-1">
                            <AuthorityDot rank={s.authority_rank} />
                            <span className={s.status === "deprecated" || s.status === "historical" ? "text-muted-foreground line-through" : ""}>{s.label}</span>
                          </span>
                          <span className="font-medium">{s.value}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-1.5 rounded bg-background/70 p-1.5 text-[11px]">
                      <span className="font-medium text-success">Resolved:</span> {cf.resolution}
                    </div>
                  </div>
                ))}
              </TabsContent>
            )}

            {hasTrace && (
              <TabsContent value="reasoning" className="pt-1.5">
                <ol className="relative ml-2 space-y-2 border-l border-border pl-3">
                  {meta.trace.map((t, i) => (
                    <li key={i} className="relative">
                      <span className="absolute -left-[18px] top-1 h-2 w-2 rounded-full border border-background bg-primary" />
                      <div className="text-sm font-medium">{t.label}</div>
                      {t.detail && <div className="text-[11px] text-muted-foreground">{t.detail}</div>}
                    </li>
                  ))}
                </ol>
              </TabsContent>
            )}

            {hasTools && (
              <TabsContent value="tools" className="space-y-1 pt-1.5">
                {meta.tool_calls.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1.5 text-xs">
                    {t.ok ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <XCircle className="h-3.5 w-3.5 text-destructive" />}
                    <code className="font-medium">{t.tool}</code>
                    <span className="truncate text-muted-foreground">{t.summary}</span>
                    <span className="ml-auto shrink-0 text-muted-foreground">{t.latency_ms}ms</span>
                  </div>
                ))}
              </TabsContent>
            )}
          </Tabs>
        </div>
      )}
      <SourceDocumentDialog target={docTarget} onClose={() => setDocTarget(null)} />
    </div>
  );
}
