"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

type MobileNavContextValue = {
  open: boolean;
  setOpen: (v: boolean) => void;
  openNav: () => void;
  closeNav: () => void;
};

const MobileNavContext = createContext<MobileNavContextValue | null>(null);

export function MobileNavProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const openNav = useCallback(() => setOpen(true), []);
  const closeNav = useCallback(() => setOpen(false), []);
  const value = useMemo(
    () => ({ open, setOpen, openNav, closeNav }),
    [open, openNav, closeNav]
  );
  return <MobileNavContext.Provider value={value}>{children}</MobileNavContext.Provider>;
}

export function useMobileNav() {
  const ctx = useContext(MobileNavContext);
  if (!ctx) {
    throw new Error("useMobileNav must be used within MobileNavProvider");
  }
  return ctx;
}
