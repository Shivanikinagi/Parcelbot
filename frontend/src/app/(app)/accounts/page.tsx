"use client";

import { Building2, Star } from "lucide-react";
import { useAccounts } from "@/lib/queries";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function AccountsPage() {
  const { data, isLoading } = useAccounts();
  return (
    <div>
      <PageHeader title="Accounts" description="Customer accounts in your scope." />
      <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-44" />)
          : data?.map((a: any) => (
              <Card key={a.code}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Building2 className="h-4 w-4 text-primary" /> {a.name}
                    </CardTitle>
                    {a.premium_support && <Badge variant="warning"><Star className="h-3 w-3" /> Premium</Badge>}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{a.code}</span> · <span className="capitalize">{a.plan}</span> · <span className="capitalize">{a.status}</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Health</span>
                      <span className={a.health_score < 70 ? "text-destructive" : a.health_score < 90 ? "text-warning" : "text-success"}>{a.health_score}</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div className={`h-full rounded-full ${a.health_score < 70 ? "bg-destructive" : a.health_score < 90 ? "bg-warning" : "bg-success"}`} style={{ width: `${a.health_score}%` }} />
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">CSM: <span className="text-foreground">{a.csm || "—"}</span></div>
                  {a.notes && <p className="text-xs text-muted-foreground line-clamp-3">{a.notes}</p>}
                </CardContent>
              </Card>
            ))}
        {data?.length === 0 && <p className="text-sm text-muted-foreground">No accounts in your scope.</p>}
      </div>
    </div>
  );
}
