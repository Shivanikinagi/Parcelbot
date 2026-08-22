"use client";

import {
  Activity,
  AlertTriangle,
  Boxes,
  Building2,
  Lightbulb,
  Repeat,
  Ticket,
  Truck,
  ArrowUpRight,
  Search,
} from "lucide-react";
import { useDashboard } from "@/lib/queries";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { SeverityBadge, StatusPill } from "@/components/common/badges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading || !data) {
    return (
      <div>
        <PageHeader title="Operations" description="Proactive issue detection across your accounts." />
        <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }

  const t = data.totals;
  return (
    <div>
      <PageHeader title="Operations" description="Proactive issue detection across your accounts." />
      <div className="space-y-7 p-6">
        {/* KPIs */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard label="Accounts" value={t.accounts} icon={Building2} />
          <StatCard label="Open tickets" value={t.open_tickets} icon={Ticket} tone="warning" />
          <StatCard label="Orders" value={t.orders} icon={Boxes} />
          <StatCard label="SLA breaches" value={t.sla_breaches} icon={AlertTriangle} tone={t.sla_breaches ? "destructive" : "success"} />
          <StatCard label="Escalations" value={t.escalations} icon={ArrowUpRight} />
        </div>

        {/* AI insights */}
        <Card className="border-primary/30 bg-primary/[0.03]">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-primary" /> AI Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {data.ai_insights.map((s: string, i: number) => (
              <div key={i} className="rounded-lg border border-border/50 bg-background/40 px-3 py-2 text-sm leading-relaxed">
                {s}
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          {/* High severity tickets */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Activity className="h-4 w-4" /> High-severity tickets</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {data.high_severity_tickets.length === 0 && <Empty />}
              {data.high_severity_tickets.map((r: any) => (
                <div key={r.code} className="flex items-center gap-3 rounded-lg border border-border/60 p-3">
                  <SeverityBadge severity={r.severity} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{r.subject}</div>
                    <div className="text-xs text-muted-foreground">{r.code} · {r.account}</div>
                  </div>
                  {r.breached ? <Badge variant="destructive">SLA breached</Badge> : <Badge variant="muted">{r.sla_target}</Badge>}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* SLA breaches */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><AlertTriangle className="h-4 w-4 text-destructive" /> SLA breaches</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {data.sla_breaches.length === 0 && <Empty label="No breaches — all within target." />}
              {data.sla_breaches.map((r: any) => (
                <div key={r.code} className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
                  <SeverityBadge severity={r.severity} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{r.code} · {r.account}</div>
                    <div className="text-xs text-muted-foreground">Target {r.sla_target} · {r.source.replace(/_/g, " ")}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Recurring problems */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Repeat className="h-4 w-4" /> Recurring problems</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {data.recurring_problems.length === 0 && <Empty />}
              {data.recurring_problems.map((k: any) => (
                <div key={k.code} className="rounded-lg border border-border/60 p-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="warning">{k.code}</Badge>
                    <span className="text-sm font-medium">{k.title}</span>
                    <Badge variant="muted" className="ml-auto">{k.count}×</Badge>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground line-clamp-2">{k.guidance}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Customer health */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Building2 className="h-4 w-4" /> Customer health</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {data.customer_health.map((a: any) => (
                <div key={a.code}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium">{a.name} <span className="text-xs capitalize text-muted-foreground">· {a.plan}</span></span>
                    <span className={a.health_score < 70 ? "text-destructive" : a.health_score < 90 ? "text-warning" : "text-success"}>{a.health_score}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div className={`h-full rounded-full ${a.health_score < 70 ? "bg-destructive" : a.health_score < 90 ? "bg-warning" : "bg-success"}`} style={{ width: `${a.health_score}%` }} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Carrier problems */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Truck className="h-4 w-4" /> Carrier problems</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {data.carrier_problems.map((c: any) => (
                <div key={c.carrier} className="flex items-center justify-between rounded-lg border border-border/60 p-2.5 text-sm">
                  <span className="font-medium">{c.carrier}</span>
                  <span className="text-muted-foreground">{c.orders} orders · <span className={c.fault_orders ? "text-destructive" : ""}>{c.fault_orders} at fault</span></span>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Open investigations */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><Search className="h-4 w-4" /> Open investigations</CardTitle></CardHeader>
            <CardContent className="space-y-2.5">
              {data.open_investigations.map((k: any) => (
                <div key={k.code} className="flex items-center gap-2 rounded-lg border border-border/60 p-3">
                  <Badge variant="warning">{k.code}</Badge>
                  <span className="text-sm">{k.title}</span>
                  <StatusPill status={k.status} />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Recent escalations */}
        <Card>
          <CardHeader className="pb-3"><CardTitle className="flex items-center gap-2 text-base"><ArrowUpRight className="h-4 w-4" /> Recent escalations</CardTitle></CardHeader>
          <CardContent className="space-y-2.5">
            {data.recent_escalations.length === 0 && <Empty label="No escalations yet." />}
            {data.recent_escalations.map((e: any) => (
              <div key={e.code} className="flex items-center gap-3 rounded-lg border border-border/60 p-3">
                <Badge variant="muted">{e.code}</Badge>
                <SeverityBadge severity={e.severity} />
                <span className="min-w-0 flex-1 truncate text-sm">{e.reason}</span>
                <span className="text-xs text-muted-foreground">→ {e.assigned_to}</span>
                <StatusPill status={e.status} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Empty({ label = "Nothing here right now." }: { label?: string }) {
  return <div className="py-4 text-center text-sm text-muted-foreground">{label}</div>;
}
