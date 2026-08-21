"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAnalytics } from "@/lib/queries";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const PALETTE = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#64748b"];
const SEV_COLOR: Record<string, string> = { P1: "#ef4444", P2: "#f59e0b", P3: "#64748b" };

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className="h-64">{children}</CardContent>
    </Card>
  );
}

const tooltipStyle = {
  background: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
  color: "hsl(var(--popover-foreground))",
};

export default function AnalyticsPage() {
  const { data, isLoading } = useAnalytics();

  if (isLoading || !data) {
    return (
      <div>
        <PageHeader title="Analytics" description="Support performance across your accounts." />
        <div className="grid gap-4 p-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-64" />)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Analytics" description="Support performance across your accounts." />
      <div className="grid gap-4 p-6 lg:grid-cols-2">
        <ChartCard title="Ticket volume by day">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.ticket_volume}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Severity distribution">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data.severity_distribution} dataKey="count" nameKey="severity" innerRadius={45} outerRadius={80} paddingAngle={3}>
                {data.severity_distribution.map((e: any) => <Cell key={e.severity} fill={SEV_COLOR[e.severity]} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
          <Legend items={data.severity_distribution.map((e: any) => ({ label: e.severity, color: SEV_COLOR[e.severity], value: e.count }))} />
        </ChartCard>

        <ChartCard title="SLA compliance (open tickets)">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data.sla_compliance} dataKey="count" nameKey="label" innerRadius={45} outerRadius={80} paddingAngle={3}>
                {data.sla_compliance.map((e: any, i: number) => <Cell key={i} fill={e.label === "Breached" ? "#ef4444" : "#22c55e"} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
          <Legend items={data.sla_compliance.map((e: any) => ({ label: e.label, color: e.label === "Breached" ? "#ef4444" : "#22c55e", value: e.count }))} />
        </ChartCard>

        <ChartCard title="Carrier failures (at-fault shipments)">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.carrier_failures} layout="vertical">
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis type="category" dataKey="carrier" width={90} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top issues (known-issue matches)">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_issues}>
              <XAxis dataKey="code" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Support load by agent">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.support_load}>
              <XAxis dataKey="agent" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted))" }} />
              <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function Legend({ items }: { items: { label: string; color: string; value: number }[] }) {
  return (
    <div className="mt-2 flex flex-wrap justify-center gap-3">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color }} /> {i.label} ({i.value})
        </span>
      ))}
    </div>
  );
}
