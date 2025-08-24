import pandas as pd
import sqlite3
import os
import matplotlib.pyplot as plt
from geopy.distance import great_circle
import numpy as np
from datetime import timedelta

# --- Configurações e Conexão ---
# Dentro do ambiente Docker, o caminho é relativo à raiz do projeto (/app)
DB_PATH = os.path.join('data', 'sptrans_data.db')
conn = sqlite3.connect(DB_PATH)

print(f"Conectado ao banco de dados em: {DB_PATH}")

# Carrega a tabela de resultados da análise
# Usamos a tabela processada pelo analise_onibus.py
try:
    query = "SELECT * FROM resultados_analise WHERE horario_previsto_chegada IS NOT NULL;"
    df = pd.read_sql_query(query, conn)
    print(f"{len(df)} registros carregados da tabela 'resultados_analise'.")
except pd.io.sql.DatabaseError:
    print("Erro: A tabela 'resultados_analise' não foi encontrada ou está vazia.")
    print("Por favor, execute a análise principal primeiro com: docker-compose run --rm analise")
    df = pd.DataFrame()

if not df.empty:
    # --- Análise 1: Tempo Restante de Viagem (Métrica Refatorada e Corrigida) ---
    print("\n--- Iniciando Análise 1: Tempo Restante de Viagem ---\n")

    # Converte as colunas de texto para o formato de data e hora (datetime)
    df['horario_posicao'] = pd.to_datetime(df['horario_posicao']).dt.tz_localize(None)
    df['data_coleta'] = df['horario_posicao'].dt.date
    
    # Combina a data com o horário previsto para criar um datetime inicial
    df['horario_previsto_chegada_dt'] = pd.to_datetime(df['data_coleta'].astype(str) + ' ' + df['horario_previsto_chegada'])

    # --- LÓGICA DE CORREÇÃO DA VIRADA DO DIA ---
    # Condição: a hora da previsão é anterior à hora da posição? (ex: pos 23:50, prev 00:10)
    # Isso indica que a previsão é para o dia seguinte.
    condicao_virada_dia = df['horario_previsto_chegada_dt'].dt.time < df['horario_posicao'].dt.time

    # Aplica a correção: onde a condição for verdadeira, adiciona 1 dia
    # Usamos np.where para uma operação vetorizada e eficiente
    df['horario_previsto_chegada_dt'] = np.where(
        condicao_virada_dia,
        df['horario_previsto_chegada_dt'] + timedelta(days=1),
        df['horario_previsto_chegada_dt']
    )
    # É necessário converter de volta para datetime, pois np.where pode retornar um array de objetos
    df['horario_previsto_chegada_dt'] = pd.to_datetime(df['horario_previsto_chegada_dt'])
    
    # Calcula a diferença em minutos, que representa o tempo de viagem restante previsto
    df['tempo_restante_viagem_min'] = (df['horario_previsto_chegada_dt'] - df['horario_posicao']).dt.total_seconds() / 60

    # Exibe o resultado com a nova coluna
    print("Exemplo de dados com a métrica 'Tempo Restante de Viagem' CORRIGIDA:")
    print(df[['id_onibus', 'letreiro_linha', 'horario_previsto_chegada_dt', 'horario_posicao', 'tempo_restante_viagem_min']].head())

    # Calcula o tempo médio por linha
    tempo_medio_por_linha = df.groupby('letreiro_linha')['tempo_restante_viagem_min'].mean().sort_values()

    # Cria o gráfico de barras horizontais
    tempo_medio_por_linha.plot(kind='barh', figsize=(12, 8))
    plt.xlabel('Tempo Restante Médio de Viagem (Minutos)')
    plt.ylabel('Linha de Ônibus')
    plt.title('Tempo Restante Médio de Viagem por Linha (Corrigido)')
    plt.grid(axis='x', linestyle='--')
    plt.tight_layout()
    # Salva o gráfico em um arquivo em vez de mostrar na tela
    plt.savefig('reports/tempo_restante_por_linha.png')
    print("Gráfico 'Tempo Restante Médio de Viagem por Linha' salvo em reports/tempo_restante_por_linha.png")
    plt.close() # Fecha a figura para não exibir no log


    # --- Análise 2: Detecção de Ônibus Parados (Nova Métrica) ---
    print("\n--- Iniciando Análise 2: Detecção de Ônibus Parados ---\n")

    # Agrupa os dados por ônibus para analisar o histórico de posições de cada um
    analise_parada = df.sort_values('horario_posicao').groupby('id_onibus').agg(
        primeira_posicao_dt=('horario_posicao', 'first'),
        ultima_posicao_dt=('horario_posicao', 'last'),
        primeira_lat=('posicao_atual_lat', 'first'),
        primeira_lon=('posicao_atual_lon', 'first'),
        ultima_lat=('posicao_atual_lat', 'last'),
        ultima_lon=('posicao_atual_lon', 'last'),
        letreiro_linha=('letreiro_linha', 'first'),
        contagem_registros=('id_onibus', 'count')
    )

    # Filtra apenas ônibus que tiveram mais de um registro para podermos comparar
    analise_parada = analise_parada[analise_parada['contagem_registros'] > 1].copy()

    # Calcula o tempo decorrido em minutos entre a primeira e a última posição registrada
    analise_parada['tempo_decorrido_min'] = (analise_parada['ultima_posicao_dt'] - analise_parada['primeira_posicao_dt']).dt.total_seconds() / 60

    # Calcula a distância percorrida em KM usando geopy
    analise_parada['distancia_km'] = analise_parada.apply(
        lambda row: great_circle(
            (row['primeira_lat'], row['primeira_lon']),
            (row['ultima_lat'], row['ultima_lon'])
        ).kilometers,
        axis=1
    )

    # Define os critérios para um "ônibus parado"
    # Ex: Mais de 10 minutos se passaram, mas o ônibus andou menos de 100 metros (0.1 km)
    onibus_parados = analise_parada[
        (analise_parada['tempo_decorrido_min'] > 10) &
        (analise_parada['distancia_km'] < 0.1)
    ].sort_values(by='tempo_decorrido_min', ascending=False)

    if onibus_parados.empty:
        print("Nenhum ônibus atendeu aos critérios de 'parado' (mais de 10 min com deslocamento < 100m).")
    else:
        print(f"Encontrados {len(onibus_parados)} ônibus potencialmente parados/presos no trânsito:")
        print(onibus_parados[['letreiro_linha', 'tempo_decorrido_min', 'distancia_km']])

        # Gráfico para a nova análise
        contagem_parados_por_linha = onibus_parados.groupby('letreiro_linha').size().sort_values()
        if not contagem_parados_por_linha.empty:
            contagem_parados_por_linha.plot(kind='barh', figsize=(12, 8))
            plt.xlabel('Número de Ônibus Parados Detectados')
            plt.ylabel('Linha de Ônibus')
            plt.title('Contagem de Ônibus Potencialmente Parados por Linha')
            plt.grid(axis='x', linestyle='--')
            plt.tight_layout()
            # Salva o gráfico em um arquivo
            plt.savefig('reports/onibus_parados_por_linha.png')
            print("Gráfico 'Contagem de Ônibus Potencialmente Parados por Linha' salvo em reports/onibus_parados_por_linha.png")
            plt.close() # Fecha a figura

# Fecha a conexão com o banco
conn.close()
print("\nAnálise exploratória concluída.")