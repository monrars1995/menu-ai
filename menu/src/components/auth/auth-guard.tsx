"use client";

import { useAuth } from "@/lib/auth";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/loading";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <Spinner size={28} />
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}