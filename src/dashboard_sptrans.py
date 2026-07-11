"""
Dashboard Streamlit de análise da frota SPTrans.

Modos de consulta:
  - Legado: SQLite (data/sptrans_data.db)
  - Analítico: DuckDB sobre Parquet (data/parquet/) com fallback SQLite

Uso:
    streamlit run src/dashboard_sptrans.py
"""

import os

import pandas as pd
import streamlit as st
from geopy.distance import great_circle

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Análise SPTrans",
    page_icon="🚌",
    layout="wide",
)

DB_PATH = os.path.join("data", "sptrans_data.db")
PARQUET_DIR = os.path.join("data", "parquet")
CSV_PATH = os.path.join("data", "todas_as_linhas.csv")


# --- Funções de Carregamento de Dados ---


@st.cache_data
def load_data():
    """Carrega dados da tabela resultados_analise, tentando Parquet→DuckDB primeiro."""
    parquet_result = os.path.join(PARQUET_DIR, "resultados_analise")
    if os.path.isdir(parquet_result):
        try:
            import duckdb

            con = duckdb.connect()
            df = con.execute(
                "SELECT * EXCLUDE (dt) FROM read_parquet('" + parquet_result + "/**/*.parquet')"
            ).fetchdf()
            con.close()
            if not df.empty:
                df["timestamp_analise"] = pd.to_datetime(df["timestamp_analise"])
                st.sidebar.success("Modo: DuckDB + Parquet")
                return df
        except Exception:
            pass

    # Fallback: SQLite
    import sqlite3

    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT timestamp_analise, id_onibus, letreiro_linha, "
            "posicao_atual_lat, posicao_atual_lon FROM resultados_analise;",
            conn,
        )
        conn.close()
        if not df.empty:
            df["timestamp_analise"] = pd.to_datetime(df["timestamp_analise"])
            st.sidebar.info("Modo: SQLite (legado)")
            return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
    return None


@st.cache_data
def load_line_names(csv_path):
    """Carrega o mapeamento de linhas do arquivo CSV."""
    if not os.path.exists(csv_path):
        return None
    try:
        df_linhas = pd.read_csv(csv_path)
        df_linhas["nome_linha"] = df_linhas["sentido_ida"] + " / " + df_linhas["sentido_volta"]
        return df_linhas
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de nomes de linha: {e}")
        return None


def enrich_with_line_names(result_df, lines_df):
    """Adiciona nomes descritivos das linhas ao dataframe de resultado."""
    if lines_df is None or result_df.empty:
        result_df["nome_linha"] = result_df.index
        return result_df.set_index("nome_linha")

    result_df_copy = result_df.reset_index().rename(columns={"index": "letreiro_linha"})
    result_df_copy["letreiro_numerico"] = result_df_copy["letreiro_linha"].apply(lambda x: x.split("-")[0])
    result_df_copy["tipo_letreiro"] = result_df_copy["letreiro_linha"].apply(
        lambda x: int(x.split("-")[1]) if "-" in x else 10
    )

    lines_df_copy = lines_df.copy()
    lines_df_copy["letreiro_numerico"] = lines_df_copy["letreiro_numerico"].astype(str)
    lines_df_copy["tipo_letreiro"] = pd.to_numeric(lines_df_copy["tipo_letreiro"])

    enriched_df = pd.merge(
        result_df_copy,
        lines_df_copy[["letreiro_numerico", "tipo_letreiro", "nome_linha"]],
        on=["letreiro_numerico", "tipo_letreiro"],
        how="left",
    )
    enriched_df["nome_linha"] = enriched_df["nome_linha"].fillna(enriched_df["letreiro_linha"])
    enriched_df.set_index("nome_linha", inplace=True)

    original_cols = [col for col in result_df.columns]
    return enriched_df[original_cols]


@st.cache_data
def analyze_stuck_buses(df):
    """Processa o dataframe para identificar ônibus parados."""
    df_copy = df.copy()
    df_copy["horario_posicao_dt"] = pd.to_datetime(df_copy["timestamp_analise"])

    analise_parada = (
        df_copy.sort_values("horario_posicao_dt")
        .groupby("id_onibus")
        .agg(
            letreiro_linha=("letreiro_linha", "first"),
            tempo_decorrido_min=(
                "horario_posicao_dt",
                lambda x: (x.max() - x.min()).total_seconds() / 60,
            ),
            distancia_km=(
                "posicao_atual_lat",
                lambda x: (
                    great_circle(
                        (
                            x.iloc[0],
                            df_copy.loc[x.index[0], "posicao_atual_lon"],
                        ),
                        (
                            x.iloc[-1],
                            df_copy.loc[x.index[-1], "posicao_atual_lon"],
                        ),
                    ).kilometers
                    if len(x) > 1
                    else 0
                ),
            ),
        )
    )
    return analise_parada[(analise_parada["tempo_decorrido_min"] > 10) & (analise_parada["distancia_km"] < 0.1)]


@st.cache_data
def analyze_bunched_buses(df, threshold_meters=200):
    """Processa o dataframe para identificar 'comboios' de ônibus."""
    bunched_events = []
    for (timestamp, letreiro), group in df.groupby(["timestamp_analise", "letreiro_linha"]):
        if len(group) > 1:
            group_sorted = group.sort_values("posicao_atual_lat")
            for i in range(len(group_sorted) - 1):
                bus1 = group_sorted.iloc[i]
                bus2 = group_sorted.iloc[i + 1]
                distancia = great_circle(
                    (bus1.posicao_atual_lat, bus1.posicao_atual_lon),
                    (bus2.posicao_atual_lat, bus2.posicao_atual_lon),
                ).meters
                if distancia < threshold_meters:
                    bunched_events.append({"letreiro_linha": letreiro})
    return pd.DataFrame(bunched_events)


# --- Título e Carregamento de Dados ---
st.title("🚌 Dashboard de Análise da Frota SPTrans")
st.markdown(
    "Este painel apresenta insights sobre a operação da frota de ônibus de São Paulo, "
    "com base nos dados coletados da API Olho Vivo."
)

df_raw = load_data()
df_linhas = load_line_names(CSV_PATH)

if df_raw is None or df_raw.empty:
    st.warning(
        "Ainda não há dados para exibir ou o banco de dados não foi encontrado. "
        "Por favor, inicie os coletores e aguarde a geração de dados."
    )
else:
    # --- Barra Lateral ---
    st.sidebar.header("Sobre o Projeto")
    st.sidebar.info(
        "Este é um projeto de portfólio de Engenharia de Dados que demonstra "
        "uma pipeline completa: coleta, armazenamento, processamento e visualização de dados."
    )
    st.sidebar.header("Filtros")
    linhas_unicas = sorted(df_raw["letreiro_linha"].unique().tolist())
    linha_selecionada = st.sidebar.selectbox("Filtrar por Linha (para o mapa)", ["Todas"] + linhas_unicas)

    # --- Filtragem de Dados ---
    df_mapa = df_raw.copy()
    if linha_selecionada != "Todas":
        df_mapa = df_raw[df_raw["letreiro_linha"] == linha_selecionada]

    # --- Análises ---
    onibus_parados_df = analyze_stuck_buses(df_raw)
    bunched_df = analyze_bunched_buses(df_raw)

    # --- KPIs ---
    st.header("Visão Geral da Coleta")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Registros Coletados", f"{len(df_raw):,}".replace(",", "."))
    kpi2.metric("Linhas Monitoradas", df_raw["letreiro_linha"].nunique())
    kpi3.metric("Eventos de 'Comboio' Detectados", len(bunched_df))

    # Função para carregar métricas de qualidade ETL da pasta dedicada
    @st.cache_data
    def load_etl_insights(relatorios_path):
        """Carrega relatórios de qualidade de dados da pasta analise_banco_dados/relatorios/."""
        try:
            # Carregar amostra previsões (taxa de completude)
            previsoes_path = os.path.join(relatorios_path, "amostra_previsoes_completas.txt")
            if os.path.exists(previsoes_path):
                df_previsoes = pd.read_csv(
                    previsoes_path, names=["letreiro_linha", "num_regs", "taxa_previsao"], sep="|"
                )
                df_previsoes["taxa_previsao"] = df_previsoes["taxa_previsao"] * 100  # Para %
            else:
                df_previsoes = pd.DataFrame()

            # Carregar geografia linhas top
            geo_path = os.path.join(relatorios_path, "geografia_linhas_top.txt")
            if os.path.exists(geo_path):
                df_geo = pd.read_csv(geo_path, names=["letreiro_linha", "avg_lat", "avg_lon", "num_posicoes"], sep="|")
            else:
                df_geo = pd.DataFrame()

            # Carregar CSV de métricas (se existir)
            csv_path = os.path.join(relatorios_path, "metrica_linhas_top.csv")
            if os.path.exists(csv_path):
                df_csv = pd.read_csv(csv_path)
                df_csv["id_onibus"] = df_csv["id_onibus"].astype(int)  # Contagem
            else:
                df_csv = pd.DataFrame()

            return df_previsoes, df_geo, df_csv
        except Exception as e:
            st.error(f"Erro ao carregar insights ETL: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Carregar insights ETL
    relatorios_path = "analise_banco_dados/relatorios"
    df_previsoes, df_geo, df_csv = load_etl_insights(relatorios_path)

    # --- Abas para organizar o conteúdo ---
    tab_mapa, tab_parados, tab_comboios, tab_qualidade = st.tabs(
        ["📍 Mapa da Frota", "🛑 Ônibus Parados", "🚍 Comboios de Ônibus", "📊 Qualidade ETL e Insights"]
    )

    with tab_mapa:
        st.subheader(f"Exibindo a última posição conhecida para: {linha_selecionada}")
        df_mapa_latest = df_mapa.sort_values("timestamp_analise").drop_duplicates(subset=["id_onibus"], keep="last")
        df_mapa_latest = df_mapa_latest.rename(columns={"posicao_atual_lat": "lat", "posicao_atual_lon": "lon"})
        if not df_mapa_latest[["lat", "lon"]].empty:
            st.map(df_mapa_latest[["lat", "lon"]].dropna())
        else:
            st.warning("Não há dados de localização para a seleção atual.")

    with tab_parados:
        st.subheader("Detecção de Anomalias: Ônibus Parados")
        st.markdown(
            "A análise abaixo identifica ônibus que ficaram parados por mais de "
            "10 minutos com deslocamento inferior a 100 metros, um forte indicador "
            "de problemas como quebras ou trânsito extremo."
        )
        if onibus_parados_df.empty:
            st.success("Nenhum ônibus atendeu aos critérios de 'parado' durante o período analisado.")
        else:
            st.write(f"**Resultado:** Encontrados **{len(onibus_parados_df)}** ônibus potencialmente parados.")
            contagem_por_linha = onibus_parados_df.groupby("letreiro_linha").size().sort_values(ascending=False)
            contagem_enriquecida = enrich_with_line_names(contagem_por_linha.to_frame(name="contagem"), df_linhas)
            st.dataframe(contagem_enriquecida)
            st.info(
                """
            **Interpretando a Contagem:** A coluna 'contagem' representa o número de
            **veículos únicos** de cada linha que atenderam aos critérios de 'parado'.

            Um valor de '1' indica que um único ônibus daquela linha apresentou essa
            anomalia durante todo o período de coleta. O resultado sugere que os problemas
            de parada foram **incidentes isolados** em diversas linhas, e não um problema
            crônico concentrado em uma única linha.
            """
            )
            st.markdown(
                "**Comentário:** As linhas listadas acima foram as que apresentaram maior "
                "incidência de ônibus parados, sugerindo rotas com maior potencial de "
                "problemas operacionais ou de trânsito."
            )

    with tab_comboios:
        st.subheader("Detecção de Anomalias: Comboios de Ônibus")
        st.markdown(
            "Esta análise detecta eventos onde múltiplos ônibus da mesma linha se "
            "agrupam a menos de 200 metros um do outro, um sinal de irregularidade "
            "na frequência."
        )
        if bunched_df.empty:
            st.success("Nenhum evento de 'comboio' foi detectado.")
        else:
            st.write(f"**Resultado:** Detectados **{len(bunched_df)}** eventos de 'comboio'.")
            contagem_por_linha = bunched_df.groupby("letreiro_linha").size().sort_values(ascending=False)
            contagem_enriquecida = enrich_with_line_names(contagem_por_linha.to_frame(name="contagem"), df_linhas)
            st.bar_chart(contagem_enriquecida["contagem"])
            st.markdown(
                "**Comentário:** O gráfico acima mostra as linhas com maior ocorrência de "
                "'comboios'. Linhas com muitas ocorrências podem ter problemas de "
                "regularidade na operação, causando longas esperas para passageiros "
                "seguidas da chegada de múltiplos veículos juntos."
            )

    with tab_qualidade:
        st.subheader("Qualidade de Dados ETL e Insights Gerados")
        st.markdown(
            "Esta aba mostra métricas de qualidade do ETL ( %% completude de previsões) e insights geográficos para linhas top, baseado em análises filtradas na pasta `analise_banco_dados/relatorios/`."
        )

        if not df_previsoes.empty:
            st.subheader("Taxa de Completude de Previsões por Linha (Top 10)")
            st.bar_chart(df_previsoes.set_index("letreiro_linha")["taxa_previsao"], use_container_width=True)
            st.dataframe(df_previsoes.round(2))
            st.info("Linhas com >80%% de completude são ideais para análises de tempo de chegada confiáveis.")

        if not df_geo.empty:
            st.subheader("Métricas Geográficas: Centroides de Rotas para Linhas Top")
            df_geo_display = df_geo.copy()
            df_geo_display["regiao_estimada"] = df_geo_display.apply(
                lambda row: (
                    "Centro SP"
                    if -23.55 < row["avg_lat"] < -23.57 and -46.65 < row["avg_lon"] < -46.55
                    else "Zona Leste"
                    if row["avg_lon"] > -46.65
                    else "Zona Oeste"
                ),
                axis=1,
            )
            linha_geo = st.selectbox(
                "Selecione uma linha para detalhes geográficos:", df_geo_display["letreiro_linha"].tolist()
            )
            if linha_geo:
                linha_details = df_geo_display[df_geo_display["letreiro_linha"] == linha_geo].iloc[0]
                col1, col2, col3 = st.columns(3)
                col1.metric("Avg Latitude", f"{linha_details['avg_lat']:.6f}")
                col2.metric("Avg Longitude", f"{linha_details['avg_lon']:.6f}")
                col3.metric("Número de Posições", linha_details["num_posicoes"])
                st.info(
                    f"Região estimada: {linha_details['regiao_estimada']} – Ideal para otimização de rotas locais."
                )
            st.dataframe(df_geo_display.round(6))

        if not df_csv.empty:
            st.subheader("Métricas Detalhadas de Linhas Confiáveis (de Análise Filtrada)")
            linha_csv = st.selectbox(
                "Selecione uma linha do CSV para visualizar:", df_csv.index.tolist() if not df_csv.empty else []
            )
            if linha_csv:
                st.dataframe(df_csv.loc[linha_csv:linha_csv].round(6))
            else:
                st.dataframe(df_csv.round(6))
            st.info("Contagens de registros por linha após filtro de dados completos; útil para priorizar dashboard.")

        if not df_csv.empty:
            st.subheader("Tendências Geográficas nas Linhas Top")
            df_plot = df_csv.reset_index()
            col_plot1, col_plot2 = st.columns(2)
            with col_plot1:
                st.bar_chart(df_plot.set_index("letreiro_linha")["id_onibus"])
            with col_plot2:
                st.line_chart(df_plot.set_index("letreiro_linha")[["posicao_atual_lat", "posicao_atual_lon"]])
            st.info(
                "Gráficos interativos: Barras para volume; Linha para variação geográfica por linha – clique para zoom."
            )

        if df_previsoes.empty and df_geo.empty and df_csv.empty:
            st.warning(
                "Nenhum relatório de insights disponível ainda. Execute análises para gerar dados na pasta relatorios/."
            )
