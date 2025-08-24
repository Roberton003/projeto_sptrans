#!/bin/bash
# Script para automatizar a execução do painel interativo Streamlit dos ônibus de SP

set -e

# Ativa o ambiente virtual ou cria se não existir
echo "[INFO] Verificando ambiente virtual..."
if [ ! -d "venv" ]; then
    echo "[INFO] Criando ambiente virtual Python..."
    python3 -m venv venv
fi
source venv/bin/activate

# Instala as dependências
if [ -f requirements.txt ]; then
    echo "[INFO] Instalando dependências..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[ERRO] requirements.txt não encontrado!"
    exit 1
fi

# Executa o painel interativo Streamlit
echo "[INFO] Iniciando painel interativo..."
streamlit run painel_interativo_sp.py &

# Aguarda o servidor iniciar e abre no navegador padrão
sleep 3
xdg-open http://localhost:8501

echo "[SUCESSO] Painel interativo aberto no navegador!"
