"""
Menu.AI — Script de inicialização Python
Use: python3 start.py
"""
import os
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
DEV_POSTGRES_URL = "postgresql+psycopg2://menuai:menuai123@127.0.0.1:5432/menuai_db"
SUPABASE_PROJECT_URL = "https://mnqpgpckgqevepgfobzn.supabase.co"


def check_env():
    env_file = BASE / ".env"
    example_file = BASE / ".env.example"

    if not env_file.exists():
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("\n⚠️  Arquivo .env criado a partir do exemplo.")
        else:
            env_file.write_text(
                "OPENROUTER_API_KEY=sua_chave_aqui\n"
                "OPENROUTER_DEFAULT_MODEL=queen-3.6\n"
                f"DATABASE_URL={DEV_POSTGRES_URL}\n"
                f"SUPABASE_URL={SUPABASE_PROJECT_URL}\n"
            )

    content = env_file.read_text()
    if "sua_chave" in content:
        print("\n" + "=" * 60)
        print("  CONFIGURAÇÃO NECESSÁRIA")
        print("=" * 60)
        print("  Edite o arquivo .env e configure o OpenRouter:")
        print()
        print("  OPENROUTER_API_KEY=sk-or-v1-...")
        print("  OPENROUTER_DEFAULT_MODEL=queen-3.6")
        print("  IDs disponíveis: queen-3.6, glm-5-1, kimi-k2.5")
        print()
        print(f"  Arquivo: {env_file}")
        print("=" * 60)
        input("\n  Pressione Enter depois de configurar o .env...")
        # Recarrega
        content = env_file.read_text()
        if "sua_chave" in content:
            print("\n❌ Chave ainda não configurada. Encerrando.")
            sys.exit(1)


def check_deps():
    try:
        import fastapi, uvicorn, pandas, litellm  # noqa
        print("  ✅ Dependências OK")
    except ImportError as e:
        print(f"  📦 Instalando dependências... ({e.name} não encontrado)")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=BASE
        )
        if result.returncode != 0:
            print("  ❌ Erro ao instalar dependências.")
            print("     Tente manualmente: pip install -r requirements.txt")
            sys.exit(1)
        print("  ✅ Dependências instaladas")


def check_database_url():
    from dotenv import load_dotenv

    load_dotenv(BASE / ".env")
    url = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print("\n❌ Configure SUPABASE_DB_URL ou DATABASE_URL.")
        sys.exit(1)
    if url.startswith("sqlite"):
        print("\n❌ SQLite não é suportado neste fluxo.")
        print(f"   Use DATABASE_URL={DEV_POSTGRES_URL} ou SUPABASE_DB_URL do projeto Supabase.")
        sys.exit(1)


def main():
    print()
    print("🍽️  Menu.AI — Gerador de Cardápios com IA")
    print("==========================================")

    check_env()
    check_deps()
    check_database_url()

    # Garante diretórios
    (BASE / "data" / "uploads").mkdir(parents=True, exist_ok=True)

    port = int(os.getenv("PORT", "8000"))
    print(f"\n🚀 Iniciando servidor...")
    print(f"   → Acesse: http://localhost:{port}")
    print(f"   → Pressione Ctrl+C para parar\n")

    from dotenv import load_dotenv
    load_dotenv()
    debug = os.getenv("DEBUG", "false").lower() == "true"
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=debug)


if __name__ == "__main__":
    os.chdir(BASE)
    main()
