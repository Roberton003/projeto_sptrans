import pandas as pd
import sqlite3
import os
from itertools import combinations
from geopy.distance import great_circle

# --- Funções de Análise ---

def load_data(db_path):
    """Carrega os dados da tabela de resultados do banco de dados."""
    if not os.path.exists(db_path):
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return None
    try:
        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM resultados_analise;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        print(f"Sucesso: {len(df)} registros carregados da tabela 'resultados_analise'.")
        return df
    except Exception as e:
        print(f"Erro ao carregar os dados: {e}")
        return None

def load_line_names(csv_path):
    """Carrega o mapeamento de linhas do arquivo CSV."""
    if not os.path.exists(csv_path):
        print(f"Aviso: Arquivo de nomes de linha não encontrado em {csv_path}.")
        return None
    try:
        df_linhas = pd.read_csv(csv_path)
        df_linhas['nome_linha'] = df_linhas['terminal_principal'] + ' / ' + df_linhas['terminal_secundario']
        return df_linhas
    except Exception as e:
        print(f"Erro ao carregar o arquivo de nomes de linha: {e}")
        return None

def enrich_with_line_names(result_df, lines_df):
    """Adiciona nomes descritivos das linhas ao dataframe de resultado (versão robusta)."""
    if lines_df is None or result_df.empty:
        result_df['nome_linha'] = result_df.index
        return result_df.set_index('nome_linha')

    result_df_copy = result_df.reset_index().rename(columns={'index': 'letreiro_linha'})
    result_df_copy['letreiro_numerico'] = result_df_copy['letreiro_linha'].apply(lambda x: x.split('-')[0])
    result_df_copy['tipo_letreiro'] = result_df_copy['letreiro_linha'].apply(lambda x: int(x.split('-')[1]) if '-' in x else 10)

    lines_df_copy = lines_df.copy()
    lines_df_copy['letreiro_numerico'] = lines_df_copy['letreiro_numerico'].astype(str)
    lines_df_copy['tipo_letreiro'] = pd.to_numeric(lines_df_copy['tipo_letreiro'])

    enriched_df = pd.merge(
        result_df_copy,
        lines_df_copy[['letreiro_numerico', 'tipo_letreiro', 'nome_linha']],
        on=['letreiro_numerico', 'tipo_letreiro'],
        how='left'
    )
    
    enriched_df['nome_linha'] = enriched_df['nome_linha'].fillna(enriched_df['letreiro_linha'])
    enriched_df.set_index('nome_linha', inplace=True)
    
    original_cols = [col for col in result_df.columns]
    return enriched_df[original_cols]

def analyze_stuck_buses(df, lines_df):
    """Processa o dataframe para identificar ônibus parados."""
    print("\n--- Análise 1: Detecção de Ônibus Parados ---")
    print("---" * 17 + "-")
    df_copy = df.copy()
    df_copy['horario_posicao'] = pd.to_datetime(df_copy['horario_posicao'])
    
    analise_parada = df_copy.sort_values('horario_posicao').groupby('id_onibus').agg(
        letreiro_linha=('letreiro_linha', 'first'),
        tempo_decorrido_min=('horario_posicao', lambda x: (x.max() - x.min()).total_seconds() / 60),
        distancia_km=('posicao_atual_lat', lambda x: great_circle((x.iloc[0], df_copy.loc[x.index[0], 'posicao_atual_lon']), (x.iloc[-1], df_copy.loc[x.index[-1], 'posicao_atual_lon'])).kilometers if len(x) > 1 else 0)
    )
    
    onibus_parados = analise_parada[
        (analise_parada['tempo_decorrido_min'] > 10) &
        (analise_parada['distancia_km'] < 0.1)
    ].sort_values(by='tempo_decorrido_min', ascending=False)

    if onibus_parados.empty:
        print("RESULTADO: Nenhum ônibus atendeu aos critérios de 'parado' (mais de 10 min com deslocamento < 100m).")
        print("\nCOMENTÁRIO: A operação parece ter fluído sem grandes interrupções ou veículos quebrados durante o período de coleta.")
    else:
        print(f"RESULTADO: Encontrados {len(onibus_parados)} ônibus potencialmente parados/presos no trânsito.")
        contagem_por_linha = onibus_parados.groupby('letreiro_linha').size().sort_values(ascending=False)
        contagem_por_linha_enriquecido = enrich_with_line_names(contagem_por_linha.to_frame(name='contagem'), lines_df)
        print(contagem_por_linha_enriquecido[['contagem']])
        
        if not contagem_por_linha_enriquecido.empty:
            linha_campea = contagem_por_linha_enriquecido.index[0]
            print(f"\nCOMENTÁRIO: A linha '{linha_campea}' foi a que mais apresentou ônibus parados, sugerindo ser uma rota com maior incidência de trânsito pesado ou problemas operacionais.")

def analyze_bunched_buses(df, lines_df, threshold_meters=200):
    """Processa o dataframe para identificar 'comboios' de ônibus."""
    print("\n--- Análise 2: Detecção de 'Comboios' de Ônibus ---")
    print("---" * 17 + "-")
    df_copy = df.copy()
    df_copy['timestamp_analise'] = pd.to_datetime(df_copy['timestamp_analise'])

    bunched_events = []
    # Usa 'letreiro_linha' para consistência
    for (timestamp, letreiro), group in df_copy.groupby(['timestamp_analise', 'letreiro_linha']):
        if len(group) > 1:
            for bus1, bus2 in combinations(group.itertuples(), 2):
                distancia = great_circle((bus1.posicao_atual_lat, bus1.posicao_atual_lon), (bus2.posicao_atual_lat, bus2.posicao_atual_lon)).meters
                if distancia < threshold_meters:
                    # Usa 'letreiro_linha' para consistência
                    bunched_events.append({'letreiro_linha': letreiro})
    
    if not bunched_events:
        print(f"RESULTADO: Nenhum evento de 'comboio' (ônibus a menos de {threshold_meters}m) foi detectado.")
        print("\nCOMENTÁRIO: A frequência das linhas monitoradas parece estar bem regulada, sem a ocorrência de múltiplos veículos no mesmo local ao mesmo tempo.")
    else:
        bunched_df = pd.DataFrame(bunched_events)
        # Usa 'letreiro_linha' para consistência
        contagem_por_linha = bunched_df.groupby('letreiro_linha').size().sort_values(ascending=False)
        contagem_por_linha_enriquecido = enrich_with_line_names(contagem_por_linha.to_frame(name='contagem'), lines_df)
        
        print(f"RESULTADO: Detectados {len(bunched_df)} eventos de 'comboio'.")
        print("\nContagem de eventos de comboio por linha:")
        print(contagem_por_linha_enriquecido[['contagem']])

        if not contagem_por_linha_enriquecido.empty:
            linha_campea = contagem_por_linha_enriquecido.index[0]
            print(f"\nCOMENTÁRIO: A linha '{linha_campea}' foi a que mais apresentou formação de 'comboios', com {contagem_por_linha_enriquecido.iloc[0]['contagem']} eventos. Isso pode indicar uma irregularidade na frequência dos veículos, causando aglomeração e longos períodos de espera para os passageiros.")

# --- Lógica Principal ---
def main():
    """Função principal que orquestra a análise e a geração de insights."""
    DB_PATH = os.path.join('data', 'sptrans_data.db')
    CSV_PATH = os.path.join('data', 'todas_as_linhas.csv')
    
    df_raw = load_data(DB_PATH)
    df_linhas = load_line_names(CSV_PATH)

    if df_raw is None or df_raw.empty:
        return

    print("\n--- RELATÓRIO FINAL DE ANÁLISE DE ANOMALIAS ---")
    print("="*50)

    # Executa as análises
    analyze_stuck_buses(df_raw, df_linhas)
    analyze_bunched_buses(df_raw, df_linhas)

    print("\n" + "="*50)
    print("Relatório concluído.")

if __name__ == "__main__":
    main()