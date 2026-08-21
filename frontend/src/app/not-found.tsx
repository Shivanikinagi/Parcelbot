import Link from "next/link";
import { Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/12 text-primary">
        <Boxes className="h-6 w-6" />
      </div>
      <div>
        <h1 className="text-3xl font-semibold">404</h1>
        <p className="mt-1 text-muted-foreground">This page could not be found.</p>
      </div>
      <Button asChild>
        <Link href="/chat">Back to workspace</Link>
      </Button>
    </div>
  );
}
