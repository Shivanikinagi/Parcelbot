"use client";

import * as React from "react";
import { AlertTriangle, FileText, GitBranch, Wrench, CheckCircle2, XCircle, Scale, ChevronDown, ChevronUp, Search, AlertCircle, Terminal, ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import type { ChatMeta } from "@/lib/types";
import { titleCase } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
    HIGH: { variant: "success", icon: ShieldCheck, label: "High confidence" },
    MEDIUM: { variant: "warning", icon: ShieldQuestion, label: "Medium confidence" },
    LOW: { variant: "destructive", icon: ShieldAlert, label: "Low confidence" },
  };
  const cfg = map[band ?? "LOW"] ?? map.LOW;
  const Icon = cfg.icon;
  return (
    <Badge variant={cfg.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {cfg.label}
      {typeof score === "number" && <span className="opacity-70">· {(score * 100).toFixed(0)}%</span>}
    </Badge>
  );
}

export function EvidencePanels({ meta }: { meta: ChatMeta }) {
  const hasSources = meta.citations?.length > 0;
  const hasConflicts = meta.conflicts?.length > 0;
  const hasTrace = meta.trace?.length > 0;
  const hasTools = meta.tool_calls?.length > 0;
  if (!hasSources && !hasConflicts && !hasTrace && !hasTools) return null;

  const [expanded, setExpanded] = React.useState(false);
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
        <div className="border-t border-border p-3 animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Answer confidence</span>
            <ConfidenceIndicator band={meta.confidence_band} score={meta.confidence} />
          </div>
          <Tabs defaultValue={first} className="space-y-3">
            <TabsList className="flex w-full flex-wrap justify-start gap-1 bg-transparent p-0">
              {hasSources && <TabsTrigger value="sources" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><SourceIcon type="customer_agreement" />Sources · {meta.citations.length}</TabsTrigger>}
              {hasConflicts && <TabsTrigger value="conflicts" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Scale className="mr-1 h-3.5 w-3.5" />Conflicts · {meta.conflicts.length}</TabsTrigger>}
              {hasTrace && <TabsTrigger value="reasoning" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><GitBranch className="mr-1 h-3.5 w-3.5" />Reasoning</TabsTrigger>}
              {hasTools && <TabsTrigger value="tools" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Wrench className="mr-1 h-3.5 w-3.5" />Tools · {meta.tool_calls.length}</TabsTrigger>}
            </TabsList>

            {hasSources && (
              <TabsContent value="sources" className="space-y-2 pt-2">
                {meta.citations.map((c) => (
                  <div key={c.marker + c.heading} className="flex items-start gap-2.5 rounded-md border border-border/60 p-2.5">
                    <span className="mt-0.5 rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary">{c.marker}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">{c.title}</span>
                        {c.status === "deprecated" && <Badge variant="destructive" className="text-[10px]">deprecated</Badge>}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">{c.heading}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <AuthorityDot rank={c.authority_rank} />
                      <Badge variant="muted" className="text-[10px]">{SOURCE_LABEL[c.source_type] ?? titleCase(c.source_type)}</Badge>
                    </div>
                  </div>
                ))}
              </TabsContent>
            )}

            {hasConflicts && (
              <TabsContent value="conflicts" className="space-y-2 pt-2">
                {meta.conflicts.map((cf, i) => (
                  <div key={i} className="rounded-md border border-warning/40 bg-warning/5 p-3">
                    <div className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                      <AlertTriangle className="h-4 w-4 text-warning" /> {cf.topic}
                    </div>
                    <div className="space-y-1">
                      {cf.sources.map((s, si) => (
                        <div key={si} className="flex items-center justify-between gap-2 text-xs">
                          <span className="flex items-center gap-1.5">
                            <AuthorityDot rank={s.authority_rank} />
                            <span className={s.status === "deprecated" || s.status === "historical" ? "text-muted-foreground line-through" : ""}>{s.label}</span>
                          </span>
                          <span className="font-medium">{s.value}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 rounded bg-background/70 p-2 text-xs">
                      <span className="font-medium text-success">Resolved:</span> {cf.resolution}
                    </div>
                  </div>
                ))}
              </TabsContent>
            )}

            {hasTrace && (
              <TabsContent value="reasoning" className="pt-2">
                <ol className="relative ml-2 space-y-2.5 border-l border-border pl-4">
                  {meta.trace.map((t, i) => (
                    <li key={i} className="relative">
                      <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-background bg-primary" />
                      <div className="text-sm font-medium">{t.label}</div>
                      {t.detail && <div className="text-xs text-muted-foreground">{t.detail}</div>}
                    </li>
                  ))}
                </ol>
              </TabsContent>
            )}

            {hasTools && (
              <TabsContent value="tools" className="space-y-1.5 pt-2">
                {meta.tool_calls.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-md border border-border/60 px-2.5 py-2 text-xs">
                    {t.ok ? <CheckCircle2 className="h-4 w-4 text-success" /> : <XCircle className="h-4 w-4 text-destructive" />}
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
    </div>
  );
}
