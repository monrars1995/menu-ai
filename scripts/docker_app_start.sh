#!/bin/sh
set -eu

echo "Menu.AI app container starting..."

python - <<'PY'
import os
import subprocess
import sys
import time

from sqlalchemy import create_engine, text

url = os.getenv("SUPABASE_DB_URL") or os.environ["DATABASE_URL"]
engine = create_engine(url, pool_pre_ping=True)

last_error = None
for attempt in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection OK.")
        break
    except Exception as exc:
        last_error = exc
        print(f"Waiting for database ({attempt + 1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready: {last_error}")

# Check if schema already exists (supabase já provisionado)
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_documents')"
    ))
    schema_exists = result.scalar()

    result = conn.execute(text(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
    ))
    alembic_exists = result.scalar()

if schema_exists and not alembic_exists:
    print("⚠️  Banco com schema existente mas sem alembic_version — aplicando stamp heads.")
    subprocess.run(["python", "-m", "alembic", "stamp", "heads"], check=True)
elif not schema_exists:
    print("✅ Banco limpo — aplicando migrations.")
    subprocess.run(["python", "-m", "alembic", "upgrade", "heads"], check=True)
else:
    print("✅ Migrations já aplicadas — verificando atualizações pendentes.")
    subprocess.run(["python", "-m", "alembic", "upgrade", "heads"], check=True)
PY

if [ "${MENUAI_RUN_SEED:-false}" = "true" ]; then
  python seed_data.py
fi

exec uvicorn app:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
