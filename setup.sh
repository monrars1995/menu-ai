#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}▶ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠  $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Menu.AI v3.2.0 — Setup Docker Desktop           ║"
echo "╚══════════════════════════════════════════════════════╝"

step "Validando Docker Desktop"
command -v docker >/dev/null 2>&1 || error "Docker não encontrado."
docker info >/dev/null 2>&1 || error "Docker Desktop não está ativo ou o daemon não responde."

step "Verificando .env"
if [ ! -f ".env" ]; then
  cp .env.example .env
  warn ".env criado a partir do exemplo."
fi

if ! grep -qE "^OPENROUTER_API_KEY=.+" .env 2>/dev/null; then
  warn "OPENROUTER_API_KEY não configurada no .env."
fi

if grep -qE "^SUPABASE_DB_URL=postgres" .env 2>/dev/null; then
  step "Modo de banco detectado: Supabase"
  warn "App e admin irão usar SUPABASE_DB_URL; o container postgres local torna-se opcional."
else
  step "Modo de banco detectado: PostgreSQL local Docker"
fi

step "Subindo stack completa"
docker compose up -d --build postgres app admin pgadmin

step "Status dos serviços"
docker compose ps

echo ""
echo "API:      http://localhost:8000"
echo "Admin:    http://localhost:8001"
echo "Swagger:  http://localhost:8000/api/docs"
echo "Admin:    http://localhost:8001/api/docs"
echo "pgAdmin:  http://localhost:5050"
echo ""
echo "Logs da API:   docker compose logs -f app"
echo "Logs do admin: docker compose logs -f admin"
