"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      router.replace(user ? "/dashboard" : "/login");
    }
  }, [user, loading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <div className="flex items-center gap-3">
        <img src="/isotipo.svg" alt="Menu.AI" className="h-10 w-10 animate-pulse" />
        <span className="text-xl font-medium tracking-tight text-ink">Menu.AI</span>
      </div>
    </div>
  );
}
