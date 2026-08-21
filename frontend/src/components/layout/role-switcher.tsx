"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ChevronsUpDown, LogOut, UserCog } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-store";
import { useDemoUsers } from "@/lib/queries";
import type { LoginResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const roleVariant: Record<string, any> = {
  customer: "secondary",
  support: "default",
  manager: "warning",
  admin: "destructive",
};

export function RoleSwitcher() {
  const { user, setAuth, logout } = useAuth();
  const { data: users } = useDemoUsers();
  const qc = useQueryClient();

  async function switchTo(email: string) {
    try {
      const res = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setAuth(res.token, res.user);
      qc.clear();
      toast.success(`Signed in as ${res.user.name}`, { description: `Role: ${res.user.role}` });
    } catch (e: any) {
      toast.error("Could not switch identity", { description: e?.message });
    }
  }

  if (!user) return null;
  const initials = user.name.split(" ").map((p) => p[0]).slice(0, 2).join("");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-auto gap-2.5 px-2 py-1.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
            {initials}
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-tight">{user.name}</span>
            <span className="block text-xs capitalize text-muted-foreground">{user.role}</span>
          </span>
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="flex items-center gap-1.5">
          <UserCog className="h-3.5 w-3.5" /> Switch identity (demo RBAC)
        </DropdownMenuLabel>
        {users?.map((u) => (
          <DropdownMenuItem key={u.id} onSelect={() => switchTo(u.email)}>
            <div className="flex w-full items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{u.name}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {u.account_name ?? "Internal staff"}
                </div>
              </div>
              <Badge variant={roleVariant[u.role]} className="capitalize">{u.role}</Badge>
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => logout()} className="text-destructive">
          <LogOut className="h-4 w-4" /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
