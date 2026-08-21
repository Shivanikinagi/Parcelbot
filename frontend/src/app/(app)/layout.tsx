"use client";

import { Boxes } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useAuthGuard } from "@/lib/use-auth-guard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { ready } = useAuthGuard();
  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Boxes className="h-5 w-5 animate-pulse-soft text-primary" />
          <span className="text-sm">Loading workspace…</span>
        </div>
      </div>
    );
  }
  return <AppShell>{children}</AppShell>;
}
