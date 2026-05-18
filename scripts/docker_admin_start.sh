#!/bin/sh
set -eu

echo "Menu.AI admin container starting..."

python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url, pool_pre_ping=True)

last_error = None
for attempt in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection OK.")
        break
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        print(f"Waiting for database ({attempt + 1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready: {last_error}")
PY

exec uvicorn admin.main:app \
  --host 0.0.0.0 \
  --port "${ADMIN_PORT:-8001}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
