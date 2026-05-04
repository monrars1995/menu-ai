#\!/bin/bash
cd "$(dirname "$0")"
echo "🍽️  Menu.AI — Iniciando..."
echo ""

# Remove venv antigo se requirements.txt foi modificado
if [ -d "venv" ] && [ "requirements.txt" -nt "venv/pyvenv.cfg" ]; then
  echo "📦 requirements.txt atualizado — recriando ambiente virtual..."
  rm -rf venv
fi

# Cria venv se não existir
if [ \! -d "venv" ]; then
  echo "📦 Criando ambiente virtual Python..."
  python3 -m venv venv
fi

# Ativa venv
source venv/bin/activate

# Instala dependências
echo "📦 Instalando dependências (pode levar alguns minutos na 1ª vez)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Erro ao instalar pacotes. Detalhes:"
  pip install -r requirements.txt
  echo ""
  read -p "Pressione Enter para fechar..." _
  exit 1
fi

echo "✅ Dependências instaladas com sucesso"
echo ""
echo "🚀 Servidor iniciando em http://localhost:8000"
echo "   Pressione Ctrl+C para parar"
echo ""

# Abre navegador automaticamente após 4s
sleep 4 && open http://localhost:8000 &

python3 app.py
