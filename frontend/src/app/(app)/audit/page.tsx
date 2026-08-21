"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { useAuditLog, useToolExecutions } from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function AuditPage() {
  const { data: audit, isLoading } = useAuditLog();
  const { data: tools } = useToolExecutions();

  return (
    <div>
      <PageHeader title="Audit & Observability" description="Every state change and tool execution, correlated by request." />
      <div className="p-6">
        <Tabs defaultValue="audit">
          <TabsList>
            <TabsTrigger value="audit">Audit log</TabsTrigger>
            <TabsTrigger value="tools">Tool executions</TabsTrigger>
          </TabsList>

          <TabsContent value="audit">
            {isLoading ? <Skeleton className="h-72" /> : (
              <div className="rounded-xl border border-border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>When</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Request</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {audit?.map((r: any) => (
                      <TableRow key={r.id}>
                        <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(r.created_at)}</TableCell>
                        <TableCell>
                          <span className="capitalize">{r.actor_role}</span>
                          {r.actor_name && <span className="ml-1 text-xs text-muted-foreground">· {r.actor_name}</span>}
                        </TableCell>
                        <TableCell><Badge variant="muted">{r.action}</Badge></TableCell>
                        <TableCell className="text-muted-foreground">{r.resource_type}{r.resource_id ? ` · ${r.resource_id}` : ""}</TableCell>
                        <TableCell>{r.success ? <CheckCircle2 className="h-4 w-4 text-success" /> : <XCircle className="h-4 w-4 text-destructive" />}</TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">{r.request_id ?? "—"}</TableCell>
                      </TableRow>
                    ))}
                    {audit?.length === 0 && <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">No audit entries yet.</TableCell></TableRow>}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>

          <TabsContent value="tools">
            <div className="rounded-xl border border-border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>When</TableHead>
                    <TableHead>Tool</TableHead>
                    <TableHead>Summary</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Result</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tools?.map((r: any) => (
                    <TableRow key={r.id}>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(r.created_at)}</TableCell>
                      <TableCell><code className="text-xs font-medium">{r.tool_name}</code></TableCell>
                      <TableCell className="max-w-[360px] truncate text-muted-foreground">{r.summary}</TableCell>
                      <TableCell className="text-xs">{r.latency_ms}ms</TableCell>
                      <TableCell>{r.success ? <CheckCircle2 className="h-4 w-4 text-success" /> : <XCircle className="h-4 w-4 text-destructive" />}</TableCell>
                    </TableRow>
                  ))}
                  {tools?.length === 0 && <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">No tool executions yet.</TableCell></TableRow>}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
