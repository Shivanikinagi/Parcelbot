"use client";

import { ShieldAlert, Check, X } from "lucide-react";
import type { PendingAction } from "@/lib/types";
import { Button } from "@/components/ui/button";

export function ConfirmationCard({
  action,
  onConfirm,
  onCancel,
  disabled,
}: {
  action: PendingAction;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="mt-3 rounded-lg border border-primary/40 bg-primary/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
        <ShieldAlert className="h-4 w-4" /> Confirmation required
      </div>
      <p className="text-sm font-medium">{action.human}</p>
      {action.consequences?.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
          {action.consequences.map((c, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-primary">•</span> {c}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={onConfirm} disabled={disabled}>
          <Check className="h-3.5 w-3.5" /> Confirm & execute
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel} disabled={disabled}>
          <X className="h-3.5 w-3.5" /> Cancel
        </Button>
      </div>
    </div>
  );
}
