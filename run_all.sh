#!/bin/bash

# Ativa o ambiente virtual
source venv/bin/activate

# Inicia o coletor de posições em background
echo "Iniciando coleta_sptrans.py em background..."
python3 coleta_sptrans.py > coleta_sptrans.log 2>&1 &
COLETA_POS_PID=$!

# Inicia o coletor de previsões em background
echo "Iniciando coleta_previsoes.py em background..."
python3 coleta_previsoes.py > coleta_previsoes.log 2>&1 &
COLETA_PREV_PID=$!

echo "Scripts de coleta iniciados!"
echo "PID do coletor de posições: $COLETA_POS_PID"
echo "PID do coletor de previsões: $COLETA_PREV_PID"
echo ""
echo "Para parar os scripts, use o comando: kill $COLETA_POS_PID $COLETA_PREV_PID"
