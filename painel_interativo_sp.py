import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(page_title="Painel Interativo Ônibus SP", layout="wide")

st.title("Painel Interativo de Posições dos Ônibus de São Paulo")

# Carregar dados
df = pd.read_csv("posicoes_onibus.csv")

# Ajuste dos nomes das colunas conforme o CSV
latitude_col = 'py'  # latitude
longitude_col = 'px'  # longitude
linha_col = 'codigo_linha'
sentido_col = 'sv'  # sentido do ônibus (0/1)
datahora_col = 'ta'  # data/hora da posição
acessibilidade_col = 'a'  # acessibilidade
codigo_onibus_col = 'p'  # código do ônibus

# Filtros interativos
linhas = sorted(df[linha_col].unique())
linha_selecionada = st.multiselect("Selecione a(s) linha(s):", linhas, default=linhas)

sentidos = sorted(df[sentido_col].unique())
sentido_selecionado = st.multiselect("Selecione o(s) sentido(s):", sentidos, default=sentidos)

# Filtrar dataframe
df_filtro = df[df[linha_col].isin(linha_selecionada) & df[sentido_col].isin(sentido_selecionado)]

# Estatísticas rápidas
col1, col2, col3 = st.columns(3)
col1.metric("Total de ônibus", df_filtro[codigo_onibus_col].nunique())
col2.metric("Total de linhas", df_filtro[linha_col].nunique())
col3.metric("Última atualização", df_filtro[datahora_col].max())

# Mapa interativo
m = folium.Map(location=[-23.55052, -46.633308], zoom_start=12, tiles='cartodbpositron')
marker_cluster = MarkerCluster().add_to(m)
dict_cores = {0: 'blue', 1: 'red'}

for _, row in df_filtro.iterrows():
    cor = dict_cores.get(row.get(sentido_col, 0), 'gray')
    acess = 'Sim' if row.get(acessibilidade_col, 0) == 1 else 'Não'
    popup_html = f"""
    <b>Ônibus:</b> {row.get(codigo_onibus_col, '')}<br>
    <b>Linha:</b> {row.get(linha_col, '')}<br>
    <b>Sentido:</b> {row.get(sentido_col, '')}<br>
    <b>Acessível:</b> {acess}<br>
    <b>Data/Hora:</b> {row.get(datahora_col, '')}
    """
    folium.CircleMarker(
        location=[row[latitude_col], row[longitude_col]],
        radius=5,
        color=cor,
        fill=True,
        fill_color=cor,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(marker_cluster)

st_folium(m, width=1200, height=700)

# Tabela de dados filtrados
with st.expander("Ver tabela de dados filtrados"):
    st.dataframe(df_filtro)
