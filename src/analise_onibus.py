import os
import sqlite3
import pandas as pd
import logging
from datetime import datetime

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_PATH = os.path.join('data', 'sptrans_data.db')

# --- Lógica Principal da Análise ---
def main():
    """Conecta ao banco de dados, executa a análise e salva o resultado na tabela `resultados_analise`."""
    logging.info("--- Iniciando script de análise de ônibus (versão final) ---")

    if not os.path.exists(DB_PATH):
        logging.error(f"Banco de dados não encontrado em {DB_PATH}. Execute o 'inicializar_banco.py' primeiro.")
        return

    conn = None # Inicializa a conexão como None
    try:
        # 1. CONECTAR AO BANCO DE DADOS
        conn = sqlite3.connect(DB_PATH)
        logging.info(f"Conectado com sucesso ao banco de dados: {DB_PATH}")

        # 2. BUSCAR POSIÇÕES NA ÚLTIMA MEIA HORA
        # Usamos a função datetime do SQLite com o modificador 'localtime' para garantir que estamos usando o fuso horário local.
        query_posicoes = "SELECT * FROM posicoes"
        logging.info("Executando query para buscar todas as posições...")
        posicoes_df = pd.read_sql_query(query_posicoes, conn)
        logging.info(f"{len(posicoes_df)} registros de posição encontrados.")

        if posicoes_df.empty:
            logging.warning("Nenhum dado de posição no banco de dados para analisar. Encerrando.")
            return

        # 3. BUSCAR PREVISÕES NA ÚLTIMA MEIA HORA
        query_previsoes = "SELECT * FROM previsoes"
        logging.info("Executando query para buscar previsões nas últimas 24 horas...")
        previsoes_df = pd.read_sql_query(query_previsoes, conn)
        logging.info(f"{len(previsoes_df)} registros de previsão encontrados.")

        # 4. PROCESSAR E UNIR OS DADOS
        previsoes_df_unicas = previsoes_df.sort_values(by='horario_previsao').drop_duplicates(subset=['id_onibus'], keep='first')
        logging.info(f"{len(previsoes_df_unicas)} previsões únicas (uma por ônibus) foram processadas.")
        logging.info("Unindo dados de posição e previsão...")
        df_final = pd.merge(posicoes_df, previsoes_df_unicas, on='id_onibus', how='left')

        # Filtrar para análises com dados completos (apenas previsões não-nulas)
        df_completa = df_final.dropna(subset=['id_parada', 'horario_previsao'])
        logging.info(f"Registros com dados completos para análise: {len(df_completa)}")

        # 5. PREPARAR DADOS PARA O BANCO DE DADOS
        # Adiciona o timestamp da análise e reordena as colunas para corresponder à tabela de destino
        df_final['timestamp_analise'] = datetime.now()
        # Renomeia colunas do DataFrame para corresponderem exatamente às da tabela SQL
        df_final.rename(columns={
            'latitude': 'posicao_atual_lat',
            'longitude': 'posicao_atual_lon',
            'timestamp_posicao': 'horario_posicao',
            'id_parada': 'proximo_ponto_previsto', # Simplificação, idealmente buscaríamos o nome do ponto
            'horario_previsao': 'horario_previsto_chegada'
        }, inplace=True)

        # Renomear também em df_completa para métricas
        df_completa = df_completa.copy()
        df_completa.rename(columns={
            'latitude': 'posicao_atual_lat',
            'longitude': 'posicao_atual_lon'
        }, inplace=True)

        # Garante que todas as colunas da tabela de destino existam no DataFrame
        colunas_tabela = ['timestamp_analise', 'id_onibus', 'letreiro_linha', 'posicao_atual_lat', 'posicao_atual_lon', 'horario_posicao', 'proximo_ponto_previsto', 'horario_previsto_chegada']
        for col in colunas_tabela:
            if col not in df_final.columns:
                df_final[col] = None # Adiciona colunas faltantes com valor Nulo (NULL)
        df_final = df_final[colunas_tabela] # Garante a ordem correta

        # Calcular métricas geográficas para linhas top (baseado em amostras)
        if not df_completa.empty:
            top_linhas = ['8000-10', '4313-10', '917H-10']
            for linha in top_linhas:
                linha_df = df_completa[df_completa['letreiro_linha'] == linha]
                if not linha_df.empty:
                    avg_lat = linha_df['posicao_atual_lat'].mean()
                    avg_lon = linha_df['posicao_atual_lon'].mean()
                    logging.info(f"Métrica para linha {linha}: Avg Lat {avg_lat:.6f}, Avg Lon {avg_lon:.6f}, Registros: {len(linha_df)}")

            # Salvar métricas como relatório (para pasta analise_banco_dados/relatorios/)
            metrica_report = df_completa[df_completa['letreiro_linha'].isin(top_linhas)].groupby('letreiro_linha').agg({
                'posicao_atual_lat': 'mean',
                'posicao_atual_lon': 'mean',
                'id_onibus': 'count'
            }).round(6)
            metrica_report.to_csv('analise_banco_dados/relatorios/metrica_linhas_top.csv', index=True)
            logging.info("Métricas geográficas salvas em analise_banco_dados/relatorios/metrica_linhas_top.csv")

        # 6. SALVAR O RESULTADO NO BANCO DE DADOS (usando df_final completo, mas análise em df_completa)
        logging.info("Limpando a tabela 'resultados_analise' antes de inserir novos dados...")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resultados_analise;")
        conn.commit()
        logging.info(f"Salvando {len(df_final)} registros de análise na tabela 'resultados_analise'...")
        df_final.to_sql('resultados_analise', conn, if_exists='append', index=False)
        logging.info("Análise concluída e resultados salvos no banco de dados!")

    except (sqlite3.Error, Exception) as e:
        logging.error(f"Ocorreu um erro durante a análise: {e}")
    finally:
        # Garante que a conexão com o banco seja sempre fechada no final.
        if conn:
            conn.close()
            logging.info("Conexão com o banco de dados fechada.")

# --- Ponto de Entrada do Script ---
if __name__ == "__main__":
    main()
