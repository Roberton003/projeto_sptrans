import streamlit as st
import pandas as pd
import sqlite3
import os
from itertools import combinations
from geopy.distance import great_circle

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Análise SPTrans",
    page_icon="🚌",
    layout="wide"
)

# --- Funções de Análise e Carregamento de Dados ---

@st.cache_data # Cache para não recarregar os dados a cada interação
def load_data(db_path):
    """Carrega os dados da tabela de resultados do banco de dados."""
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        # Carrega apenas as colunas necessárias para otimizar a memória
        query = "SELECT timestamp_analise, id_onibus, letreiro_linha, posicao_atual_lat, posicao_atual_lon FROM resultados_analise;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['timestamp_analise'] = pd.to_datetime(df['timestamp_analise'])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return None

@st.cache_data
def load_line_names(csv_path):
    """Carrega o mapeamento de linhas do arquivo CSV."""
    if not os.path.exists(csv_path):
        return None
    try:
        df_linhas = pd.read_csv(csv_path)
        df_linhas['nome_linha'] = df_linhas['sentido_ida'] + ' / ' + df_linhas['sentido_volta']
        return df_linhas
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de nomes de linha: {e}")
        return None

def enrich_with_line_names(result_df, lines_df):
    """Adiciona nomes descritivos das linhas ao dataframe de resultado."""
    if lines_df is None or result_df.empty:
        result_df['nome_linha'] = result_df.index
        return result_df.set_index('nome_linha')

    result_df_copy = result_df.reset_index().rename(columns={'index': 'letreiro_linha'})
    result_df_copy['letreiro_numerico'] = result_df_copy['letreiro_linha'].apply(lambda x: x.split('-')[0])
    result_df_copy['tipo_letreiro'] = result_df_copy['letreiro_linha'].apply(lambda x: int(x.split('-')[1]) if '-' in x else 10)

    lines_df_copy = lines_df.copy()
    lines_df_copy['letreiro_numerico'] = lines_df_copy['letreiro_numerico'].astype(str)
    lines_df_copy['tipo_letreiro'] = pd.to_numeric(lines_df_copy['tipo_letreiro'])

    enriched_df = pd.merge(result_df_copy, lines_df_copy[['letreiro_numerico', 'tipo_letreiro', 'nome_linha']], on=['letreiro_numerico', 'tipo_letreiro'], how='left')
    enriched_df['nome_linha'] = enriched_df['nome_linha'].fillna(enriched_df['letreiro_linha'])
    enriched_df.set_index('nome_linha', inplace=True)
    
    original_cols = [col for col in result_df.columns]
    return enriched_df[original_cols]

@st.cache_data
def analyze_stuck_buses(df):
    """Processa o dataframe para identificar ônibus parados."""
    df_copy = df.copy()
    df_copy['horario_posicao_dt'] = pd.to_datetime(df_copy['timestamp_analise'])
    
    analise_parada = df_copy.sort_values('horario_posicao_dt').groupby('id_onibus').agg(
        letreiro_linha=('letreiro_linha', 'first'),
        tempo_decorrido_min=('horario_posicao_dt', lambda x: (x.max() - x.min()).total_seconds() / 60),
        distancia_km=('posicao_atual_lat', lambda x: great_circle((x.iloc[0], df_copy.loc[x.index[0], 'posicao_atual_lon']), (x.iloc[-1], df_copy.loc[x.index[-1], 'posicao_atual_lon'])).kilometers if len(x) > 1 else 0)
    )
    return analise_parada[(analise_parada['tempo_decorrido_min'] > 10) & (analise_parada['distancia_km'] < 0.1)]

@st.cache_data
def analyze_bunched_buses(df, threshold_meters=200):
    """Processa o dataframe para identificar 'comboios' de ônibus."""
    bunched_events = []
    for (timestamp, letreiro), group in df.groupby(['timestamp_analise', 'letreiro_linha']):
        if len(group) > 1:
            # Sort by latitude to make proximity checks more efficient
            group_sorted = group.sort_values('posicao_atual_lat')
            
            # Check distance between consecutive buses after sorting
            # This is a simplification and might miss some bunched buses
            # but it's much faster than combinations for large groups
            for i in range(len(group_sorted) - 1):
                bus1 = group_sorted.iloc[i]
                bus2 = group_sorted.iloc[i+1]
                distancia = great_circle((bus1.posicao_atual_lat, bus1.posicao_atual_lon), (bus2.posicao_atual_lat, bus2.posicao_atual_lon)).meters
                if distancia < threshold_meters:
                    bunched_events.append({'letreiro_linha': letreiro})
    return pd.DataFrame(bunched_events)

# --- Título e Carregamento de Dados ---
st.title("🚌 Dashboard de Análise da Frota SPTrans")
st.markdown("Este painel apresenta insights sobre a operação da frota de ônibus de São Paulo, com base nos dados coletados da API Olho Vivo.")

DB_PATH = os.path.join('data', 'sptrans_data.db')
CSV_PATH = os.path.join('data', 'todas_as_linhas.csv')

df_raw = load_data(DB_PATH)
df_linhas = load_line_names(CSV_PATH)

if df_raw is None or df_raw.empty:
    st.warning("Ainda não há dados para exibir ou o banco de dados não foi encontrado. Por favor, inicie os coletores e aguarde a geração de dados.")
else:
    # --- Barra Lateral ---
    st.sidebar.header("Sobre o Projeto")
    st.sidebar.info("Este é um projeto de portfólio de Engenharia de Dados que demonstra uma pipeline completa: coleta, armazenamento, processamento e visualização de dados.")
    st.sidebar.header("Filtros")
    linhas_unicas = sorted(df_raw['letreiro_linha'].unique().tolist())
    linha_selecionada = st.sidebar.selectbox("Filtrar por Linha (para o mapa)", ["Todas"] + linhas_unicas)

    # --- Filtragem de Dados ---
    df_mapa = df_raw.copy()
    if linha_selecionada != "Todas":
        df_mapa = df_raw[df_raw['letreiro_linha'] == linha_selecionada]

    # --- Análises ---
    onibus_parados_df = analyze_stuck_buses(df_raw)
    bunched_df = analyze_bunched_buses(df_raw)

    # --- KPIs ---
    st.header("Visão Geral da Coleta")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Registros Coletados", f"{len(df_raw):,}".replace(",", "."))
    kpi2.metric("Linhas Monitoradas", df_raw['letreiro_linha'].nunique())
    kpi3.metric("Eventos de 'Comboio' Detectados", len(bunched_df))

    # --- Abas para organizar o conteúdo ---
    tab_mapa, tab_parados, tab_comboios = st.tabs(["📍 Mapa da Frota", "🛑 Ônibus Parados", "🚍 Comboios de Ônibus"])

    with tab_mapa:
        st.subheader(f"Exibindo a última posição conhecida para: {linha_selecionada}")
        df_mapa_latest = df_mapa.sort_values('timestamp_analise').drop_duplicates(subset=['id_onibus'], keep='last')
        df_mapa_latest = df_mapa_latest.rename(columns={'posicao_atual_lat': 'lat', 'posicao_atual_lon': 'lon'})
        if not df_mapa_latest[['lat', 'lon']].empty:
            st.map(df_mapa_latest[['lat', 'lon']].dropna())
        else:
            st.warning("Não há dados de localização para a seleção atual.")

    with tab_parados:
        st.subheader("Detecção de Anomalias: Ônibus Parados")
        st.markdown("A análise abaixo identifica ônibus que ficaram parados por mais de 10 minutos com deslocamento inferior a 100 metros, um forte indicador de problemas como quebras ou trânsito extremo.")
        if onibus_parados_df.empty:
            st.success("Nenhum ônibus atendeu aos critérios de 'parado' durante o período analisado.")
        else:
            st.write(f"**Resultado:** Encontrados **{len(onibus_parados_df)}** ônibus potencialmente parados.")
            contagem_por_linha = onibus_parados_df.groupby('letreiro_linha').size().sort_values(ascending=False)
            contagem_enriquecida = enrich_with_line_names(contagem_por_linha.to_frame(name='contagem'), df_linhas)
            st.dataframe(contagem_enriquecida)
            
            st.info("""
            **Interpretando a Contagem:** A coluna 'contagem' representa o número de **veículos únicos** de cada linha que atenderam aos critérios de 'parado'. 
            
            Um valor de '1' indica que um único ônibus daquela linha apresentou essa anomalia durante todo o período de coleta. O resultado sugere que os problemas de parada foram **incidentes isolados** em diversas linhas, e não um problema crônico concentrado em uma única linha.
            """)

            st.markdown("**Comentário:** As linhas listadas acima foram as que apresentaram maior incidência de ônibus parados, sugerindo rotas com maior potencial de problemas operacionais ou de trânsito.")

    with tab_comboios:
        st.subheader("Detecção de Anomalias: Comboios de Ônibus")
        st.markdown("Esta análise detecta eventos onde múltiplos ônibus da mesma linha se agrupam a menos de 200 metros um do outro, um sinal de irregularidade na frequência.")
        if bunched_df.empty:
            st.success("Nenhum evento de 'comboio' foi detectado.")
        else:
            st.write(f"**Resultado:** Detectados **{len(bunched_df)}** eventos de 'comboio'.")
            contagem_por_linha = bunched_df.groupby('letreiro_linha').size().sort_values(ascending=False)
            contagem_enriquecida = enrich_with_line_names(contagem_por_linha.to_frame(name='contagem'), df_linhas)
            st.bar_chart(contagem_enriquecida['contagem'])
            st.markdown("**Comentário:** O gráfico acima mostra as linhas com maior ocorrência de 'comboios'. Linhas com muitas ocorrências podem ter problemas de regularidade na operação, causando longas esperas para passageiros seguidas da chegada de múltiplos veículos juntos.")