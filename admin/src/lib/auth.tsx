"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { setCookie, deleteCookie } from "./cookies";

interface User {
  id: string;
  nome?: string;
  email: string;
  role: string;
  empresa_id?: string;
}

interface AuthContextType {
  token: string | null;
  apiKey: string | null;
  user: User | null;
  loading: boolean;
  login: (email: string, senha: string) => Promise<string | null>;
  loginWithApiKey: (key: string) => Promise<string | null>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = "menuai_admin_token";
const API_KEY_KEY = "menuai_admin_api_key";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    const k = typeof window !== "undefined" ? localStorage.getItem(API_KEY_KEY) : null;
    setToken(t);
    setApiKey(k);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (token || apiKey) {
      refreshUser();
    }
  }, [token, apiKey]);

  async function refreshUser() {
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    else if (apiKey) headers["X-Admin-Api-Key"] = apiKey;
    else return;

    try {
      const res = await fetch("/api/admin/info", { headers });
      if (!res.ok) {
        if (res.status === 401) logout();
        return;
      }
      const data = await res.json();
      setUser({
        id: data.usuario_id || data.id,
        nome: data.nome,
        email: data.email,
        role: data.role,
        empresa_id: data.empresa_id,
      });
    } catch {
      // ignore
    }
  }

  async function login(email: string, senha: string): Promise<string | null> {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha }),
    });
    if (!res.ok) {
      const text = await res.text();
      return text || "Falha no login.";
    }
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setCookie(TOKEN_KEY, data.access_token);
      deleteCookie(API_KEY_KEY);
      localStorage.removeItem(API_KEY_KEY);
      setToken(data.access_token);
      setApiKey(null);
      return null;
    }
    return "Resposta inesperada.";
  }

  async function loginWithApiKey(key: string): Promise<string | null> {
    localStorage.removeItem(TOKEN_KEY);
    deleteCookie(TOKEN_KEY);
    setToken(null);
    const res = await fetch("/api/admin/info", {
      headers: { "X-Admin-Api-Key": key },
    });
    if (!res.ok) {
      return "Chave administrativa inválida.";
    }
    localStorage.setItem(API_KEY_KEY, key);
    setCookie(API_KEY_KEY, key);
    setApiKey(key);
    return null;
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(API_KEY_KEY);
    deleteCookie(TOKEN_KEY);
    deleteCookie(API_KEY_KEY);
    setToken(null);
    setApiKey(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, apiKey, user, loading, login, loginWithApiKey, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
