#!/bin/bash
# Script para automatizar a geração do painel de ônibus de SP

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

# Executa o script Python
echo "[INFO] Gerando painel..."
python3 painel_onibus_sp.py

# Abre o painel no navegador padrão
echo "[INFO] Abrindo painel no navegador..."
xdg-open painel_onibus_sp.html

echo "[SUCESSO] Painel gerado e aberto no navegador!"
