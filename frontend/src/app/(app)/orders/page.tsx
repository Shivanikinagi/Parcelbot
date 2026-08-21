"use client";

import { useOrders } from "@/lib/queries";
import { formatDateTime, inr } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { StatusPill } from "@/components/common/badges";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function OrdersPage() {
  const { data, isLoading } = useOrders();
  return (
    <div>
      <PageHeader title="Orders" description="Shipments in your scope." />
      <div className="p-6">
        {isLoading ? (
          <Skeleton className="h-72" />
        ) : (
          <div className="rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Account</TableHead>
                  <TableHead>Carrier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Fee</TableHead>
                  <TableHead>Pickup window</TableHead>
                  <TableHead>Flags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((o: any) => (
                  <TableRow key={o.code}>
                    <TableCell className="font-medium">{o.code}</TableCell>
                    <TableCell className="text-muted-foreground">{o.account_code}</TableCell>
                    <TableCell>{o.carrier}</TableCell>
                    <TableCell><StatusPill status={o.status} /></TableCell>
                    <TableCell>{inr(o.shipment_fee_inr)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {o.pickup_window_start ? `${formatDateTime(o.pickup_window_start)} → ${formatDateTime(o.pickup_window_end)}` : "—"}
                    </TableCell>
                    <TableCell className="space-x-1">
                      {o.carrier_fault && <Badge variant="destructive" className="text-[10px]">carrier fault</Badge>}
                      {o.customer_fault && <Badge variant="warning" className="text-[10px]">customer fault</Badge>}
                      {!o.carrier_fault && !o.customer_fault && <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                  </TableRow>
                ))}
                {data?.length === 0 && (
                  <TableRow><TableCell colSpan={7} className="py-8 text-center text-muted-foreground">No orders in your scope.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
