#!/bin/bash
# Script para inicializar Git na pasta MENU I.A e conectar ao repositório remoto
# Execute: bash setup_git.sh

set -e

echo "=== Configurando Git para menu-ia-app ==="

# 1. Inicializar repositório Git local
git init

# 2. Configurar branch principal como 'main'
git branch -M main

# 3. Conectar ao repositório remoto (substitua SEU_USUARIO pelo seu username do GitHub)
# Para descobrir seu username: https://github.com
GITHUB_USER=$(git config --global user.name 2>/dev/null || echo "")

echo ""
echo "Qual é o seu username no GitHub? (ex: carlosgeilsonjr)"
read GITHUB_USER

REMOTE_URL="https://github.com/${GITHUB_USER}/menu-ia-app.git"
echo "Conectando ao repositório: $REMOTE_URL"

git remote add origin "$REMOTE_URL"

# 4. Adicionar todos os arquivos (respeitando o .gitignore)
git add .

# 5. Verificar o que será commitado
echo ""
echo "=== Arquivos que serão commitados ==="
git status --short

# 6. Fazer o primeiro commit
git commit -m "feat: primeiro commit - estrutura inicial do Menu.AI

- Aplicação FastAPI com pipeline multi-etapas (LiteLLM + LangChain)
- Routers: cardápios, ingredientes, fichas técnicas, empresas, contratos
- Database: modelos SQLAlchemy + Alembic migrations
- Tools: ferramentas de IA para geração de cardápios
- Docker Compose configurado
- Ambiente: requirements.txt + .env.example"

# 7. Enviar para o GitHub
echo ""
echo "=== Enviando para o GitHub ==="
git push -u origin main

echo ""
echo "✅ Pronto! Código enviado para https://github.com/${GITHUB_USER}/menu-ia-app"
