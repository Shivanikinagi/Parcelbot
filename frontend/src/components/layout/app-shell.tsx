"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  Boxes,
  Building2,
  ClipboardList,
  MessageSquare,
  ScrollText,
  Settings,
  Ticket,
} from "lucide-react";
import { useAuth } from "@/lib/auth-store";
import { useSystemInfo } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { RoleSwitcher } from "./role-switcher";
import { ThemeToggle } from "./theme-toggle";

interface NavItem {
  href: string;
  label: string;
  icon: any;
  show: (role: string) => boolean;
}

const ALL = () => true;
const INTERNAL = (r: string) => ["support", "manager", "admin"].includes(r);
const MANAGER = (r: string) => ["manager", "admin"].includes(r);

const NAV: { section: string; items: NavItem[] }[] = [
  {
    section: "Workspace",
    items: [
      { href: "/chat", label: "Support Chat", icon: MessageSquare, show: ALL },
      { href: "/dashboard", label: "Operations", icon: Activity, show: INTERNAL },
      { href: "/analytics", label: "Analytics", icon: BarChart3, show: MANAGER },
    ],
  },
  {
    section: "Records",
    items: [
      { href: "/tickets", label: "Tickets", icon: Ticket, show: ALL },
      { href: "/orders", label: "Orders", icon: Boxes, show: ALL },
      { href: "/accounts", label: "Accounts", icon: Building2, show: ALL },
      { href: "/knowledge", label: "Knowledge Base", icon: BookOpen, show: ALL },
    ],
  },
  {
    section: "System",
    items: [
      { href: "/history", label: "Conversations", icon: ClipboardList, show: ALL },
      { href: "/audit", label: "Audit Logs", icon: ScrollText, show: MANAGER },
      { href: "/settings", label: "Settings", icon: Settings, show: ALL },
    ],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { data: sys } = useSystemInfo();
  const role = user?.role ?? "customer";

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card/40 md:flex">
        <div className="flex h-14 items-center gap-2 border-b border-border px-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Boxes className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">ParcelPilot</span>
          <Badge variant="muted" className="ml-auto text-[10px]">AI</Badge>
        </div>
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
          {NAV.map((group) => {
            const items = group.items.filter((i) => i.show(role));
            if (!items.length) return null;
            return (
              <div key={group.section}>
                <div className="px-2 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  {group.section}
                </div>
                <div className="space-y-0.5">
                  {items.map((item) => {
                    const active = pathname === item.href || pathname.startsWith(item.href + "/");
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                          active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>
        <div className="border-t border-border p-3 text-[11px] text-muted-foreground">
          {sys && (
            <div className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", sys.llm_mode === "live" ? "bg-success" : "bg-warning")} />
              LLM: {sys.llm_mode === "live" ? sys.llm_model : "offline mock"}
            </div>
          )}
          <div className="mt-1">Snapshot: {sys?.reference_time ?? "—"} IST</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-5">
          <div className="md:hidden flex items-center gap-2">
            <Boxes className="h-5 w-5 text-primary" />
            <span className="font-semibold">ParcelPilot</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            <RoleSwitcher />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
