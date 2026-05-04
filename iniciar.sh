#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "Menu.AI - Docker Desktop"
echo "========================"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ".env criado a partir do exemplo."
fi

docker info >/dev/null 2>&1 || {
  echo "Docker Desktop não está ativo."
  exit 1
}

docker compose up -d --build postgres app admin
docker compose ps

echo ""
echo "API:   http://localhost:8000"
echo "Admin: http://localhost:8001"
echo ""
