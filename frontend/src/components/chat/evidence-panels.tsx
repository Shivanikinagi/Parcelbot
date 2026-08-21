"use client";

import { AlertTriangle, FileText, GitBranch, Wrench, CheckCircle2, XCircle, Scale } from "lucide-react";
import type { ChatMeta } from "@/lib/types";
import { titleCase } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

export function EvidencePanels({ meta }: { meta: ChatMeta }) {
  const hasSources = meta.citations?.length > 0;
  const hasConflicts = meta.conflicts?.length > 0;
  const hasTrace = meta.trace?.length > 0;
  const hasTools = meta.tool_calls?.length > 0;
  if (!hasSources && !hasConflicts && !hasTrace && !hasTools) return null;

  const first = hasSources ? "sources" : hasConflicts ? "conflicts" : hasTrace ? "reasoning" : "tools";

  return (
    <Tabs defaultValue={first} className="mt-3 rounded-lg border border-border bg-background/50 p-3">
      <TabsList className="flex w-full flex-wrap justify-start">
        {hasSources && <TabsTrigger value="sources"><FileText className="mr-1 h-3.5 w-3.5" />Sources · {meta.citations.length}</TabsTrigger>}
        {hasConflicts && <TabsTrigger value="conflicts"><Scale className="mr-1 h-3.5 w-3.5" />Conflicts · {meta.conflicts.length}</TabsTrigger>}
        {hasTrace && <TabsTrigger value="reasoning"><GitBranch className="mr-1 h-3.5 w-3.5" />Reasoning</TabsTrigger>}
        {hasTools && <TabsTrigger value="tools"><Wrench className="mr-1 h-3.5 w-3.5" />Tools · {meta.tool_calls.length}</TabsTrigger>}
      </TabsList>

      {hasSources && (
        <TabsContent value="sources" className="space-y-2">
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
        <TabsContent value="conflicts" className="space-y-2">
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
        <TabsContent value="reasoning">
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
        <TabsContent value="tools" className="space-y-1.5">
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
  );
}
