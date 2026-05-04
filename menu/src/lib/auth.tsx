"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "./supabase";
import api from "./api";
import type { User } from "./types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, senha: string) => Promise<string | null>;
  loginWithSupabase: () => Promise<string | null>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = "menuai_token";
const COOKIE_KEY = "menuai_token";

function setCookie(name: string, value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax`;
}

function storeToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  setCookie(COOKIE_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  deleteCookie(COOKIE_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function syncUserFromApi() {
    try {
      const u = await api.auth.me();
      setUser(u);
    } catch {
      setUser(null);
    }
  }

  async function refreshUser() {
    await syncUserFromApi();
  }

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    if (token) {
      setCookie(COOKIE_KEY, token);
      syncUserFromApi().finally(() => setLoading(false));
    } else {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (event === "SIGNED_IN" && session) {
          storeToken(session.access_token);
          await syncUserFromApi();
        } else if (event === "SIGNED_OUT") {
          clearToken();
          setUser(null);
        }
      });

      supabase.auth.getSession().then(async ({ data: { session } }) => {
        if (session?.access_token) {
          storeToken(session.access_token);
          await syncUserFromApi();
        }
        setLoading(false);
      });

      return () => subscription.unsubscribe();
    }
  }, []);

  async function login(email: string, senha: string): Promise<string | null> {
    try {
      const data = await api.auth.login(email, senha);
      storeToken(data.access_token);
      setUser(data.usuario);
      return null;
    } catch (e: any) {
      return e?.message || "Falha no login.";
    }
  }

  async function loginWithSupabase(): Promise<string | null> {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/dashboard` },
      });
      if (error) return error.message;
      return null;
    } catch (e: any) {
      return e?.message || "Falha no login com Google.";
    }
  }

  async function logout() {
    clearToken();
    await supabase.auth.signOut();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithSupabase, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
