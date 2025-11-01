import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- Configuração ---
st.set_page_config(page_title="Comparação ETL vs Moovit", layout="wide")
DB_PATH = os.path.join('data', 'sptrans_data.db')

def load_own_data(line="1036-10"):
    """Carrega dados da linha 1036-10 do DB, focando horários."""
    if not os.path.exists(DB_PATH):
        st.error(f"DB não encontrado: {DB_PATH}")
        return pd.DataFrame(), pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        # Posições
        df_pos = pd.read_sql(f"SELECT timestamp_coleta, latitude, longitude, letreiro_linha FROM posicoes WHERE letreiro_linha = '{line}' ORDER BY timestamp_coleta DESC LIMIT 50;", conn)
        df_pos['timestamp_coleta'] = pd.to_datetime(df_pos['timestamp_coleta'])
        # Previsões
        df_prev = pd.read_sql(f"SELECT timestamp_coleta, id_parada, horario_previsao FROM previsoes WHERE id_linha = 1036 ORDER BY timestamp_coleta DESC LIMIT 50;", conn)
        df_prev['timestamp_coleta'] = pd.to_datetime(df_prev['timestamp_coleta'])
        conn.close()
        return df_pos, df_prev
    except Exception as e:
        st.error(f"Erro carregando dados: {e}")
        return pd.DataFrame(), pd.DataFrame()

def scrape_moovit_line(line="1036-10"):
    """Scrape Moovit for predictions using curl (fallback simulado, use MCP for real)."""
    # Nota: Para real, use requests or selenium in script, but here output placeholder
    st.info("Simulação Moovit scrape (use tool real for live): linha 1036-10 intervalos 10-15min, horários 5:15-23:15.")
    # In real, use brightdata-mcp but here fake for plan
    # Exemplo Moovit: chegada prevista 5-15min
    # Para comparação, assume year-month-day for full datetime
    base_date = '2025-08-15'
    # Parse with format
    timestamp_moovit1 = datetime.strptime(f'{base_date} 21:45', '%Y-%m-%d %H:%M')
    timestamp_moovit2 = datetime.strptime(f'{base_date} 21:50', '%Y-%m-%d %H:%M')
    return pd.DataFrame({
        'timestamp': [timestamp_moovit1 - timedelta(minutes=15), timestamp_moovit2 - timedelta(minutes=10)],
        'previsao_moovit': ['Chegada estimada 10min', 'Chegada estimada 5min']
    }) # Simulado; in ACT full integrate MCP

def compare_timestamps(df_pos, moovit_times):
    """Comparar horários coleta vs Moovit estimados."""
    if df_pos.empty:
        st.warning("Nenhum dado de posição para comparação.")
        return pd.DataFrame()
    # Extrair hora do timestamp para comparação simples
    df_own = df_pos[['timestamp_coleta']].copy()
    df_own['hora_our'] = df_own['timestamp_coleta'].dt.hour
    matches = []
    for _, row in df_own.iterrows():
        hora_our = row['timestamp_coleta'].hour
        closest_moovit = min(moovit_times, key=lambda t: abs(t.hour - hora_our))
        gap_min = abs((row['timestamp_coleta'] - closest_moovit).total_seconds() / 60)
        matches.append({
            'our_timestamp': row['timestamp_coleta'],
            'our_hour': hora_our,
            'moovit_hour': closest_moovit.hour,
            'gap_min': gap_min
        })
    df_match = pd.DataFrame(matches)
    return df_match.describe()

st.title("Comparação Real ETL vs Moovit/SPTrans - Linha 1036-10")

df_pos, df_prev = load_own_data()
st.write(f"Posições DB: {len(df_pos)} | Previsões DB: {len(df_prev)}")

df_moovit = scrape_moovit_line()

if st.button("Executar Comparação (simulada)"):
    stats = compare_timestamps(df_pos, df_moovit['timestamp'])
    st.dataframe(stats)
    st.info("Gaps >10min indicam perda ETL; para real, integre MCP scrape.")
