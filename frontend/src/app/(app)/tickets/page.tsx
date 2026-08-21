"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useTickets } from "@/lib/queries";
import { formatDateTime } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { SeverityBadge, StatusPill } from "@/components/common/badges";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function TicketsPage() {
  const { data, isLoading } = useTickets();
  const [selected, setSelected] = React.useState<string | null>(null);

  return (
    <div>
      <PageHeader title="Tickets" description="Support cases in your scope, with live severity and SLA." />
      <div className="p-6">
        {isLoading ? (
          <Skeleton className="h-72" />
        ) : (
          <div className="rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticket</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Account</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>SLA</TableHead>
                  <TableHead>Assigned</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((t: any) => (
                  <TableRow key={t.code} className="cursor-pointer" onClick={() => setSelected(t.code)}>
                    <TableCell className="font-medium">{t.code}</TableCell>
                    <TableCell className="max-w-[260px] truncate">{t.subject}</TableCell>
                    <TableCell className="text-muted-foreground">{t.account_code}</TableCell>
                    <TableCell><SeverityBadge severity={t.severity} /></TableCell>
                    <TableCell><StatusPill status={t.status} /></TableCell>
                    <TableCell>
                      {t.sla ? (t.sla.breached ? <Badge variant="destructive">Breached</Badge> : <Badge variant="muted">{t.sla.target_human}</Badge>) : <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{t.assigned_to ?? "—"}</TableCell>
                  </TableRow>
                ))}
                {data?.length === 0 && (
                  <TableRow><TableCell colSpan={7} className="py-8 text-center text-muted-foreground">No tickets in your scope.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
      <TicketDetail code={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function TicketDetail({ code, onClose }: { code: string | null; onClose: () => void }) {
  const { data: t } = useQuery({
    queryKey: ["ticket", code],
    queryFn: () => apiFetch<any>(`/tickets/${code}`),
    enabled: !!code,
  });

  return (
    <Dialog open={!!code} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl">
        {t && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {t.code}
                <SeverityBadge severity={t.classified_severity?.severity} />
                <StatusPill status={t.status} />
              </DialogTitle>
              <p className="text-sm text-muted-foreground">{t.subject}</p>
            </DialogHeader>
            <div className="max-h-[60vh] space-y-4 overflow-y-auto text-sm">
              <p className="text-muted-foreground">{t.description}</p>

              <Section title="Classified severity">
                <p><SeverityBadge severity={t.classified_severity?.severity} /> {t.classified_severity?.rationale}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {t.classified_severity?.signals?.map((s: string) => <Badge key={s} variant="muted" className="text-[10px]">{s}</Badge>)}
                </div>
              </Section>

              {t.sla && (
                <Section title="SLA">
                  <p>{t.sla.explanation}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Due {formatDateTime(t.sla.due_at)} · source: {t.sla.source.replace(/_/g, " ")}</p>
                </Section>
              )}

              {t.known_issues?.length > 0 && (
                <Section title="Matching known issues">
                  {t.known_issues.map((k: any) => (
                    <div key={k.code} className="mb-1"><Badge variant="warning">{k.code}</Badge> <span className="text-xs">{k.guidance}</span></div>
                  ))}
                </Section>
              )}

              {t.historical_resolution && (
                <Section title="Historical resolution (context only — may be incorrect)">
                  <p className="italic text-muted-foreground">{t.historical_resolution}</p>
                </Section>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border/60 p-3">
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</div>
      {children}
    </div>
  );
}
