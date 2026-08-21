"use client";

import { Cpu, Clock, Database, UserCircle } from "lucide-react";
import { useAuth } from "@/lib/auth-store";
import { useSystemInfo } from "@/lib/queries";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function SettingsPage() {
  const { user } = useAuth();
  const { data: sys } = useSystemInfo();

  return (
    <div>
      <PageHeader title="Settings" description="Your identity, appearance, and platform configuration." />
      <div className="grid gap-4 p-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><UserCircle className="h-4 w-4" /> Identity</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Name" value={user?.name} />
            <Row label="Email" value={user?.email} />
            <Row label="Role" value={<Badge variant="muted" className="capitalize">{user?.role}</Badge>} />
            <Row label="Account" value={user?.account_name ?? "Internal staff"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><Cpu className="h-4 w-4" /> Platform</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="LLM mode" value={sys ? (sys.llm_mode === "live" ? <Badge variant="success">Live · {sys.llm_model}</Badge> : <Badge variant="warning">Offline mock</Badge>) : "—"} />
            <Row label="Embeddings" value={sys?.embeddings ?? "—"} icon={Database} />
            <Row label="Reference time" value={`${sys?.reference_time ?? "—"} IST`} icon={Clock} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Appearance</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Toggle light / dark theme</span>
            <ThemeToggle />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon?: any }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-1.5 last:border-0">
      <span className="flex items-center gap-1.5 text-muted-foreground">{Icon && <Icon className="h-3.5 w-3.5" />}{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
