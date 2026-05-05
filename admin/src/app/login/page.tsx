"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { KeyRound, LogIn } from "lucide-react";

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"jwt" | "apikey">("jwt");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [msg, setMsg] = useState("");
  const [isError, setIsError] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    const err = await auth.login(email, senha);
    setLoading(false);
    if (err) {
      setIsError(true);
      setMsg(err);
    } else {
      router.push("/dashboard");
    }
  }

  async function handleApiKey(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    const err = await auth.loginWithApiKey(apiKey);
    setLoading(false);
    if (err) {
      setIsError(true);
      setMsg(err);
    } else {
      router.push("/dashboard");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--surface-canvas)] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg text-white"
            style={{ background: "var(--color-brand)" }}
          >
            <svg viewBox="0 0 100 100" className="h-full w-full p-1.5" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="18" r="7" fill="currentColor" className="opacity-90" />
              <path
                d="M 24 80 V 42 C 24 34 32 30 38 36 L 50 48 L 62 36 C 68 30 76 34 76 42 V 80"
                fill="none"
                stroke="currentColor"
                strokeWidth="6.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M 50 48 V 85" fill="none" stroke="currentColor" strokeWidth="6.5" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-page-title">Menu.AI Admin</h1>
          <p className="text-subtitle">Acesso restrito a administradores</p>
        </div>

        <div className="surface p-6">
          <div className="mb-4 flex rounded-md bg-[var(--surface-subtle)] p-1">
            <button
              type="button"
              onClick={() => {
                setTab("jwt");
                setMsg("");
              }}
              className={`flex-1 rounded-sm py-2 text-xs font-medium transition-colors ${
                tab === "jwt"
                  ? "bg-white text-[var(--color-ink)] shadow-sm"
                  : "text-[var(--text-secondary)]"
              }`}
            >
              <span className="flex items-center justify-center gap-1.5">
                <LogIn size={14} />
                Login
              </span>
            </button>
            <button
              type="button"
              onClick={() => {
                setTab("apikey");
                setMsg("");
              }}
              className={`flex-1 rounded-sm py-2 text-xs font-medium transition-colors ${
                tab === "apikey"
                  ? "bg-white text-[var(--color-ink)] shadow-sm"
                  : "text-[var(--text-secondary)]"
              }`}
            >
              <span className="flex items-center justify-center gap-1.5">
                <KeyRound size={14} />
                API Key
              </span>
            </button>
          </div>

          {tab === "jwt" ? (
            <form onSubmit={handleLogin} className="space-y-3">
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                required
              />
              <input
                type="password"
                placeholder="Senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="input"
                required
              />
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Entrando…" : "Entrar"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleApiKey} className="space-y-3">
              <input
                type="password"
                placeholder="Chave administrativa"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="input"
                required
              />
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Verificando…" : "Acessar"}
              </button>
            </form>
          )}

          {msg && (
            <p className={`mt-3 text-xs ${isError ? "text-red-600" : "text-[var(--text-secondary)]"}`}>{msg}</p>
          )}
        </div>
      </div>
    </div>
  );
}
