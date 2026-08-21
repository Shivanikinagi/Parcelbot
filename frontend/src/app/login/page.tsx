"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Boxes, ArrowRight, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";
import { useDemoUsers } from "@/lib/queries";
import type { LoginResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const roleVariant: Record<string, any> = {
  customer: "secondary",
  support: "default",
  manager: "warning",
  admin: "destructive",
};
const roleBlurb: Record<string, string> = {
  customer: "Sees only their own account, orders, tickets & agreement.",
  support: "Sees assigned accounts; can act on tickets.",
  manager: "Full cross-account access + analytics & audit.",
  admin: "Full access + administration.",
};

export default function LoginPage() {
  const router = useRouter();
  const { token, setAuth, hydrated } = useAuth();
  const { data: users, isLoading } = useDemoUsers();
  const [pending, setPending] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (hydrated && token) router.replace("/chat");
  }, [hydrated, token, router]);

  async function signIn(email: string) {
    setPending(email);
    try {
      const res = await apiFetch<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email }) });
      setAuth(res.token, res.user);
      toast.success(`Welcome, ${res.user.name}`);
      router.replace("/chat");
    } catch (e: any) {
      toast.error("Sign-in failed", { description: e?.message });
      setPending(null);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand side */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-primary p-12 text-primary-foreground lg:flex">
        <div className="absolute inset-0 bg-grid opacity-10" />
        <div className="relative flex items-center gap-2">
          <Boxes className="h-6 w-6" />
          <span className="text-lg font-semibold">ParcelPilot</span>
        </div>
        <div className="relative space-y-4">
          <h1 className="text-4xl font-semibold leading-tight">Support Intelligence Platform</h1>
          <p className="max-w-md text-primary-foreground/80">
            An agentic AI that retrieves policy evidence, resolves source conflicts by authority,
            computes SLAs and eligibility deterministically, and takes audited actions — with
            role-based access enforced at the data layer.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            {["RAG + hybrid retrieval", "LangGraph agent", "Source hierarchy", "RBAC", "Confirmed actions", "Full audit"].map((t) => (
              <span key={t} className="rounded-full bg-white/10 px-3 py-1 text-xs">{t}</span>
            ))}
          </div>
        </div>
        <div className="relative flex items-center gap-2 text-sm text-primary-foreground/70">
          <ShieldCheck className="h-4 w-4" /> Mock auth, real RBAC — pick an identity to explore.
        </div>
      </div>

      {/* Identity side */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="mb-6 lg:hidden">
            <div className="flex items-center gap-2 text-lg font-semibold">
              <Boxes className="h-5 w-5 text-primary" /> ParcelPilot
            </div>
          </div>
          <h2 className="text-2xl font-semibold">Choose an identity</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Each role has a different data scope — switch anytime to see RBAC in action.
          </p>

          <div className="mt-6 space-y-2">
            {isLoading && <div className="text-sm text-muted-foreground">Loading identities…</div>}
            {users?.map((u) => (
              <Card
                key={u.id}
                onClick={() => signIn(u.email)}
                className="flex cursor-pointer items-center gap-3 p-3 transition-all hover:border-primary/50 hover:shadow-md"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/12 text-sm font-semibold text-primary">
                  {u.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{u.name}</span>
                    <Badge variant={roleVariant[u.role]} className="capitalize">{u.role}</Badge>
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {u.account_name ? `${u.account_name} · ` : "Internal · "}{roleBlurb[u.role]}
                  </div>
                </div>
                {pending === u.email ? (
                  <span className="h-4 w-4 animate-pulse-soft rounded-full bg-primary" />
                ) : (
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
