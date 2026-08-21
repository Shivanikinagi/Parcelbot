"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Search, FileText } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useDocuments } from "@/lib/queries";
import { titleCase } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function KnowledgePage() {
  const { data: docs } = useDocuments();
  const [q, setQ] = React.useState("");
  const [submitted, setSubmitted] = React.useState("");

  const { data: results, isFetching } = useQuery({
    queryKey: ["kb-search", submitted],
    queryFn: () => apiFetch<any>(`/knowledge/search?q=${encodeURIComponent(submitted)}`),
    enabled: submitted.length > 1,
  });

  return (
    <div>
      <PageHeader title="Knowledge Base" description="Policies, SOPs, product guides, and your in-scope agreements." />
      <div className="space-y-6 p-6">
        <form
          onSubmit={(e) => { e.preventDefault(); setSubmitted(q); }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the knowledge base (hybrid retrieval)…" className="pl-9" />
          </div>
          <Button type="submit" disabled={q.length < 2}>Search</Button>
        </form>

        {submitted && (
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">Results for “{submitted}”</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {isFetching && <p className="text-sm text-muted-foreground">Searching…</p>}
              {results?.conflicts?.length > 0 && (
                <div className="rounded-lg border border-warning/40 bg-warning/5 p-3 text-sm">
                  <span className="font-medium text-warning">Conflict detected: </span>
                  {results.conflicts[0].resolution}
                </div>
              )}
              {results?.passages?.map((p: any) => (
                <div key={p.marker} className="rounded-lg border border-border/60 p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary">{p.marker}</span>
                    <span className="text-sm font-medium">{p.title}</span>
                    <Badge variant="muted" className="text-[10px]">{titleCase(p.source_type)}</Badge>
                    {p.status === "deprecated" && <Badge variant="destructive" className="text-[10px]">deprecated</Badge>}
                    <span className="ml-auto text-xs text-muted-foreground">score {p.scores?.final}</span>
                  </div>
                  <div className="text-xs font-medium text-muted-foreground">{p.heading}</div>
                  <p className="mt-1 text-sm">{p.content}</p>
                </div>
              ))}
              {results && results.passages?.length === 0 && !isFetching && <p className="text-sm text-muted-foreground">No matching passages.</p>}
            </CardContent>
          </Card>
        )}

        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <BookOpen className="h-4 w-4" /> Documents in your scope
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {docs?.map((d: any) => (
              <Card key={d.code} className="p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  <div className="flex gap-1">
                    <Badge variant="muted" className="text-[10px]">{titleCase(d.source_type)}</Badge>
                    {d.internal_only && <Badge variant="secondary" className="text-[10px]">internal</Badge>}
                    {d.status === "deprecated" && <Badge variant="destructive" className="text-[10px]">deprecated</Badge>}
                  </div>
                </div>
                <div className="text-sm font-medium">{d.title}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{d.code} · {d.version}</div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
