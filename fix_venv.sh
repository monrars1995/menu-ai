#!/bin/bash
# ============================================================
# Menu.AI — Script de correção do ambiente virtual
# Execute UMA VEZ para recriar o venv limpo
# ============================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "🔧 Menu.AI — Corrigindo ambiente virtual"
echo "========================================"
echo "   Raiz do projeto: $PROJECT_DIR"

# Ordem: Homebrew / pyenv comum → Python.org em /Library/Frameworks → qualquer python3.13 / python3
if command -v python3.13 >/dev/null 2>&1; then
    PYTHON=$(command -v python3.13)
elif [ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13"
else
    PYTHON=$(command -v python3 2>/dev/null || true)
fi

if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
    echo "❌ Python 3 não encontrado. Instale Python 3.11+ (ex.: brew install python@3.13)."
    exit 1
fi

echo "✅ Python: $($PYTHON --version) ($PYTHON)"

# Remover arquivos de journal do SQLite (evitam corrupção)
if [ -f "menuai_test.db-journal" ]; then
    rm -f "menuai_test.db-journal"
    echo "🗑️  Journal SQLite removido (evita corrupção)"
fi
if [ -f "menuai_test.db-wal" ]; then
    rm -f "menuai_test.db-wal" "menuai_test.db-shm"
    echo "🗑️  WAL/SHM SQLite removidos"
fi

# Fazer backup do banco de dados se existir
if [ -f "menuai_test.db" ]; then
    cp "menuai_test.db" "menuai_test.db.backup"
    echo "✅ Backup do banco: menuai_test.db.backup"
fi

# Remover venv corrompido
echo "🗑️  Removendo venv corrompido..."
rm -rf venv

# Recriar venv limpo
echo "🔨 Recriando venv com Python 3.13..."
"$PYTHON" -m venv venv
source venv/bin/activate

# Atualizar pip
echo "📦 Atualizando pip..."
python -m pip install --upgrade pip --quiet

# Instalar dependências
echo "📦 Instalando dependências (pode demorar 2-3 min)..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Ambiente virtual recriado com sucesso!"
echo "   Python do venv: $(venv/bin/python -c 'import sys; print(sys.executable)')"
echo "🚀 Para iniciar: source venv/bin/activate && python run_server.py"
echo "📦 Migrações:   bash scripts/alembic_upgrade.sh"
echo ""
