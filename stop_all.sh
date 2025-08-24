#!/bin/bash

echo "Parando scripts de coleta..."

# Mata os processos pelo nome do arquivo de script
pkill -f coleta_sptrans.py
pkill -f coleta_previsoes.py

echo "Processos de coleta parados."
