"""
Menu.AI — Inicialização direta do servidor
Evita problemas de multiprocessing do --reload em alguns ambientes
"""
import os
import sys
from pathlib import Path

# Garante que o diretório do projeto está no path
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
os.chdir(BASE)

from dotenv import load_dotenv
load_dotenv()

import uvicorn

def ensure_dev_postgres() -> None:
    url = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "Configure SUPABASE_DB_URL ou DATABASE_URL antes de iniciar o servidor."
        )
    if url.startswith("sqlite"):
        raise RuntimeError(
            "SQLite não é suportado neste fluxo. "
            "Configure DATABASE_URL (PostgreSQL local) ou SUPABASE_DB_URL (Supabase). "
            "Veja .env.example para exemplos."
        )

if __name__ == "__main__":
    ensure_dev_postgres()
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print()
    print("🍽️  Menu.AI — Gerador de Cardápios com IA")
    print("==========================================")
    print(f"   Servidor: http://localhost:{port}")
    print(f"   Docs API: http://localhost:{port}/api/docs")
    print(f"   Modo debug: {debug}")
    print()

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,        # sem reload — evita multiprocessing issue
        log_level="info",
        access_log=True,
    )
