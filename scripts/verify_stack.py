#!/usr/bin/env python3
"""
Verificação local da stack: PostgreSQL, SELECT 1, contagens, chaves LLM, /api/health (opcional).

Uso (na raiz do repositório, venv activo):
  python3 scripts/verify_stack.py
"""
from __future__ import annotations

import os
import re
import sys

# Raiz = parent de scripts/
ROOT = __file__
for _ in range(2):
    ROOT = os.path.dirname(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Carregar .env antes de importar connection
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

# Chave usada no fluxo único de geração
_LLM_ENV_KEYS = ("OPENROUTER_API_KEY",)


def _mask_database_url(url: str) -> str:
    if not url:
        return "(vazia — usa SQLite em menuai_test.db na raiz do repo)"
    m = re.match(r"^(postgresql?://)([^:]+):([^@]+)@(.+)$", url, re.I)
    if m:
        return f"{m.group(1)}{m.group(2)}:****@{m.group(4)}"
    return url


def _llm_status() -> tuple[str, list[str]]:
    found = [k for k in _LLM_ENV_KEYS if (os.getenv(k) or "").strip()]
    if found:
        return "ok", found
    return "ausente", []


def main() -> int:
    from sqlalchemy import text

    from database.connection import DATABASE_URL, IS_SQLITE, verificar_conexao, engine

    print("— Menu.AI — verify_stack —\n")
    provider_label = "SUPABASE_DB_URL/DATABASE_URL"
    print(f"{provider_label}: {_mask_database_url(DATABASE_URL)}")
    print(f"IS_SQLITE:    {IS_SQLITE}")

    if IS_SQLITE:
        print("\nFalha: ambiente atual está em SQLite; use PostgreSQL Docker ou Supabase.")
        return 1

    if not verificar_conexao():
        print("\nFalha: conexão com o banco.")
        return 1
    print("Conexão: OK (SELECT 1)")

    with engine.connect() as conn:
        for table, label in (
            ("fichas_tecnicas", "fichas técnicas"),
            ("ingredientes", "ingredientes"),
            ("empresas", "empresas"),
        ):
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"Contagem {label}: {n}")
            except Exception as e:  # noqa: BLE001 — diagnóstico
                print(f"Contagem {label}: (tabela ausente ou erro) — {e}")

    st, keys = _llm_status()
    if st == "ok":
        print(f"LLM: OK (OpenRouter configurado: {', '.join(keys)})")
    else:
        print("LLM: OPENROUTER_API_KEY ausente — a geração real falha até configurar o .env")

    health_url = os.getenv("VERIFY_STACK_HEALTH_URL", "http://127.0.0.1:8000/api/health").strip()
    try:
        import urllib.error
        import urllib.request

        with urllib.request.urlopen(health_url, timeout=2) as r:  # nosec B310
            body = r.read().decode("utf-8", errors="replace")
        print(f"GET {health_url}: {body[:200]}{'…' if len(body) > 200 else ''}")
    except Exception as e:  # noqa: BLE001
        print(f"GET {health_url}: (servidor não acessível — {e!s}; normal se o app não estiver a correr)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
