"use client";

import Link from "next/link";
import { MessageSquare, Pin, PinOff } from "lucide-react";
import { useConversations, usePinConversation } from "@/lib/queries";
import { relativeTime } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryPage() {
  const { data, isLoading } = useConversations();
  const pin = usePinConversation();

  return (
    <div>
      <PageHeader title="Conversations" description="Your chat history — pin the ones you revisit." />
      <div className="space-y-2 p-6">
        {isLoading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14" />)}
        {data?.length === 0 && <p className="text-sm text-muted-foreground">No conversations yet. Start one in Support Chat.</p>}
        {data?.map((c) => (
          <Card key={c.id} className="flex items-center gap-3 p-3">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <Link href={`/chat?c=${c.id}`} className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{c.title}</div>
              <div className="text-xs text-muted-foreground">Updated {relativeTime(c.updated_at)}</div>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => pin.mutate({ id: c.id, pinned: !c.pinned })}
              aria-label={c.pinned ? "Unpin" : "Pin"}
            >
              {c.pinned ? <Pin className="h-4 w-4 text-primary" /> : <PinOff className="h-4 w-4 text-muted-foreground" />}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
