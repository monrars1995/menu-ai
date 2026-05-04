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
    <div className="flex min-h-screen items-center justify-center bg-[#FCFCFD] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-[#FF5A36] to-[#FF2A00] text-white">
            <svg viewBox="0 0 100 100" className="w-full h-full p-1.5" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FF5A36" />
                  <stop offset="100%" stopColor="#FF2A00" />
                </linearGradient>
              </defs>
              <circle cx="50" cy="18" r="7" fill="url(#logoGrad)" />
              <path d="M 24 80 V 42 C 24 34 32 30 38 36 L 50 48 L 62 36 C 68 30 76 34 76 42 V 80" fill="none" stroke="currentColor" strokeWidth="6.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M 50 48 V 85" fill="none" stroke="currentColor" strokeWidth="6.5" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-[#0A192F]">Menu.AI Admin</h1>
          <p className="mt-1 text-sm text-[#8892B0]">Acesso restrito a administradores</p>
        </div>

        <div className="card p-6">
          <div className="mb-4 flex rounded-lg bg-[#FCFCFD] p-1">
            <button
              onClick={() => { setTab("jwt"); setMsg(""); }}
              className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-colors ${tab === "jwt" ? "bg-white text-[#0A192F] shadow-sm" : "text-[#8892B0]"}`}
            >
              <span className="flex items-center justify-center gap-1.5">
                <LogIn size={14} />
                Login
              </span>
            </button>
            <button
              onClick={() => { setTab("apikey"); setMsg(""); }}
              className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-colors ${tab === "apikey" ? "bg-white text-[#0A192F] shadow-sm" : "text-[#8892B0]"}`}
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
            <p className={`mt-3 text-xs ${isError ? "text-red-600" : "text-[#8892B0]"}`}>
              {msg}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
