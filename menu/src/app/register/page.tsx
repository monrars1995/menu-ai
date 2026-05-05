"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { UserPlus, Eye, EyeOff } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "https://backend.neuros.my"}/api/auth/registro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome,
          email,
          senha,
          role: "nutricionista",
          empresa_id: "00000000-0000-0000-0000-000000000001",
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Erro ao criar conta." }));
        throw new Error(data.detail || "Erro ao criar conta.");
      }
      const loginErr = await login(email, senha);
      if (loginErr) {
        router.push("/login");
        return;
      }
      router.push("/dashboard");
    } catch (e: any) {
      setError(e?.message || "Erro ao criar conta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <img src="/isotipo.svg" alt="Menu.AI" className="mx-auto mb-4 h-16 w-16" />
          <h1 className="text-3xl font-medium tracking-tight text-ink">Criar conta</h1>
          <p className="mt-2 text-sm text-ink-muted-48">
            Comece a planejar cardápios inteligentes
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-xl border border-hairline bg-white p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="reg-nome" className="mb-1.5 block text-xs font-medium text-ink-muted-80">Nome</label>
              <input
                id="reg-nome"
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome completo"
                required
                className="min-h-11 w-full rounded-lg border border-hairline bg-white px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted-48 transition-colors focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
            </div>
            <div>
              <label htmlFor="reg-email" className="mb-1.5 block text-xs font-medium text-ink-muted-80">Email</label>
              <input
                id="reg-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                className="min-h-11 w-full rounded-lg border border-hairline bg-white px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-muted-48 transition-colors focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
              />
            </div>
            <div>
              <label htmlFor="reg-senha" className="mb-1.5 block text-xs font-medium text-ink-muted-80">Senha</label>
              <div className="relative">
                <input
                  id="reg-senha"
                  type={showPassword ? "text" : "password"}
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  required
                  minLength={6}
                  className="min-h-11 w-full rounded-lg border border-hairline bg-white px-3.5 py-2.5 pr-10 text-sm text-ink placeholder:text-ink-muted-48 transition-colors focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted-48 hover:text-ink transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2 disabled:opacity-50"
            >
              <UserPlus size={16} />
              {loading ? "Criando…" : "Criar conta"}
            </button>
          </form>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-center text-xs text-red-600">
              {error}
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-ink-muted-48">
          Já tem conta?{" "}
          <a href="/login" className="font-medium text-link hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border focus-visible:ring-offset-2">Entrar</a>
        </p>
      </div>
    </div>
  );
}
