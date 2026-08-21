"use client";

import Link from "next/link";
import {
  Boxes,
  ArrowRight,
  Search,
  Scale,
  ShieldCheck,
  Workflow,
  FileCheck,
  Gauge,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const FEATURES = [
  { icon: Workflow, title: "Intelligent reasoning", body: "Answers complex support questions by analyzing agreements, policies, and historical decisions — not just keywords." },
  { icon: Search, title: "Precise retrieval", body: "Finds the exact clauses and precedents that matter, ranked by authority and relevance." },
  { icon: Scale, title: "Authority-based resolution", body: "Contracts outrank policies, which outrank SOPs — conflicts are resolved and explained transparently." },
  { icon: ShieldCheck, title: "Data-level access control", body: "Customers only ever see their own accounts, orders, and tickets — enforced in the database layer." },
  { icon: FileCheck, title: "Confirmed actions only", body: "State changes are prepared, explained, confirmed, executed, then written to an immutable audit log." },
  { icon: Gauge, title: "Verified facts, not guesses", body: "SLAs, fees, and eligibility are computed in code — the agent only narrates verified results." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2 font-semibold">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Boxes className="h-4 w-4" />
          </div>
          ParcelPilot
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/login">Sign in <ArrowRight className="h-4 w-4" /></Link>
        </Button>
      </header>

      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="container relative py-24 text-center">
          <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-success" /> Enterprise Support Intelligence
          </div>
          <h1 className="mx-auto max-w-3xl text-5xl font-semibold leading-[1.1] tracking-tight">
            The support agent that <span className="text-primary">reasons, cites, and never oversteps</span>.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            ParcelPilot answers with evidence, resolves conflicting policies by authority,
            and asks before it acts — engineered for the reliability enterprises demand.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/login">Launch the platform <ArrowRight className="h-4 w-4" /></Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/chat">Open support chat</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="container pb-24">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-xl border border-border bg-card p-6 transition-shadow hover:shadow-md">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/12 text-primary">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
