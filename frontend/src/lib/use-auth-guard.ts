"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-store";

/** Redirect to /login if there is no active session (after hydration). */
export function useAuthGuard() {
  const router = useRouter();
  const { token, hydrated } = useAuth();
  useEffect(() => {
    if (hydrated && !token) router.replace("/login");
  }, [hydrated, token, router]);
  return { ready: hydrated && !!token };
}
