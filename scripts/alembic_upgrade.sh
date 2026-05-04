#!/usr/bin/env bash
# Aplica migrações Alembic usando o venv deste repositório e o DATABASE_URL do .env
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "venv/bin/activate" ]]; then
  echo "❌ venv não encontrado. Execute: bash fix_venv.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "venv/bin/activate"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

EFFECTIVE_DB_URL="${SUPABASE_DB_URL:-${DATABASE_URL:-}}"
echo "📦 Alembic (usa SUPABASE_DB_URL ou DATABASE_URL do .env)"
if [[ "${EFFECTIVE_DB_URL:-}" == sqlite:* || -z "${EFFECTIVE_DB_URL:-}" ]]; then
  echo "❌ SUPABASE_DB_URL ou DATABASE_URL deve apontar para PostgreSQL."
  exit 1
fi
exec alembic upgrade head
