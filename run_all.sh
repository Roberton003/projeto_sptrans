#!/bin/bash
echo "Iniciando os serviços de coleta de dados com Docker Compose..."
docker-compose up -d coleta-posicoes coleta-previsoes
echo "Serviços iniciados em background."