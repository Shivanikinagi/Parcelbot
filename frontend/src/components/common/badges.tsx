import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ConfidenceBadge({ band, score }: { band?: string; score?: number }) {
  const map: Record<string, { variant: any; icon: any; label: string }> = {
    HIGH: { variant: "success", icon: ShieldCheck, label: "High confidence" },
    MEDIUM: { variant: "warning", icon: ShieldQuestion, label: "Medium confidence" },
    LOW: { variant: "destructive", icon: ShieldAlert, label: "Low confidence" },
  };
  const cfg = map[band ?? "LOW"] ?? map.LOW;
  const Icon = cfg.icon;
  return (
    <Badge variant={cfg.variant}>
      <Icon className="h-3 w-3" />
      {cfg.label}
      {typeof score === "number" && <span className="opacity-70">· {(score * 100).toFixed(0)}%</span>}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity?: string | null }) {
  if (!severity) return <Badge variant="muted">—</Badge>;
  const variant = severity === "P1" ? "destructive" : severity === "P2" ? "warning" : "secondary";
  return <Badge variant={variant as any}>{severity}</Badge>;
}

export function StatusPill({ status }: { status?: string | null }) {
  if (!status) return null;
  const s = status.toLowerCase();
  const variant =
    ["open", "in_transit", "booked", "escalated", "investigating"].includes(s)
      ? "warning"
      : ["resolved", "closed", "delivered", "acknowledged"].includes(s)
        ? "success"
        : ["lost", "damaged", "breached"].includes(s)
          ? "destructive"
          : "muted";
  return <Badge variant={variant as any} className={cn("capitalize")}>{status.replace(/_/g, " ")}</Badge>;
}
