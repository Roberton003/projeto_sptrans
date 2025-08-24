import configparser
import json
import logging
import os
import time
import sqlite3
from datetime import datetime, time as time_obj

import requests
import schedule
import pandas as pd

# --- Configuração de Logging ---
LOG_FILE = 'coleta.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Configuração do Projeto ---
BASE_URL = 'http://api.olhovivo.sptrans.com.br/v2.1'
CONFIG_FILE = os.path.join('config', 'config.ini')
DB_PATH = os.path.join('data', 'sptrans_data.db')
CATALOGO_LINHAS_PATH = os.path.join('data', 'todas_as_linhas.csv')

# --- Funções de Configuração e API ---
def get_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado em: {CONFIG_FILE}")
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def get_token(config):
    try:
        return config['SPTRANS']['TOKEN']
    except KeyError:
        raise KeyError("A chave 'TOKEN' não foi encontrada na seção [SPTRANS] do arquivo de configuração.")

def get_linhas_alvo_ids(config):
    try:
        linhas_str = config['COLETA']['LINHAS_ALVO']
        return [int(x.strip()) for x in linhas_str.split(',')]
    except (KeyError, ValueError) as e:
        logging.error(f"Erro ao ler ou processar as linhas alvo do config.ini: {e}")
        return []

def get_letreiros_alvo(linhas_alvo_ids):
    """Cria um conjunto de letreiros de linha formatados (ex: '8000-10') para filtragem."""
    if not os.path.exists(CATALOGO_LINHAS_PATH):
        raise FileNotFoundError(f"Catálogo de linhas não encontrado em: {CATALOGO_LINHAS_PATH}")
    
    df_linhas = pd.read_csv(CATALOGO_LINHAS_PATH)
    # Filtra o DataFrame para manter apenas as linhas cujos IDs estão na nossa lista alvo
    df_filtrado = df_linhas[df_linhas['id_linha'].isin(linhas_alvo_ids)]
    
    # Cria o letreiro no formato 'lt-tl' e o retorna como um conjunto (set) para buscas rápidas
    letreiros_set = set(df_filtrado['letreiro_numerico'].astype(str) + '-' + df_filtrado['tipo_letreiro'].astype(str))
    logging.info(f"{len(letreiros_set)} letreiros de linha alvo carregados para filtragem.")
    return letreiros_set

def autenticar(token, session):
    url = f"{BASE_URL}/Login/Autenticar?token={token}"
    try:
        resp = session.post(url, timeout=10)
        resp.raise_for_status()
        return resp.json() is True
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de conexão durante a autenticação: {e}")
        return False

def coletar_posicoes(session):
    url = f"{BASE_URL}/Posicao"
    try:
        resp = session.get(url, timeout=45)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de conexão ao coletar posições: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Erro ao decodificar a resposta JSON da API de posições.")
        return None

# --- Job de Coleta com Filtro Inteligente ---
def job(letreiros_alvo):
    """Coleta os dados de posição, filtra pelas linhas de interesse e insere no banco."""
    horario_inicio = time_obj(5, 0)
    horario_fim = time_obj(23, 0)
    agora = datetime.now().time()

    if not (horario_inicio <= agora <= horario_fim):
        logging.info(f"Fora do horário de coleta ({agora}). Pulando execução.")
        return

    logging.info("Iniciando novo ciclo de coleta de POSIÇÕES com filtro inteligente...")
    
    try:
        config = get_config()
        token = get_token(config)
    except (FileNotFoundError, KeyError) as e:
        logging.error(f"Erro de configuração: {e}")
        return

    session = requests.Session()
    if not autenticar(token, session):
        logging.error('Não foi possível autenticar na API. Abortando ciclo.')
        return

    dados = coletar_posicoes(session)
    if not dados or not dados.get('l'):
        logging.warning('Nenhum dado de posição foi coletado neste ciclo.')
        return

    timestamp_coleta = datetime.now()
    registros_para_salvar = []
    total_veiculos_api = 0
    # O FILTRO INTELIGENTE ACONTECE AQUI!
    for linha in dados['l']:
        letreiro_linha = linha.get('c')
        total_veiculos_api += len(linha.get('vs', []))
        # Verifica se o letreiro da linha está na nossa lista de interesse
        if letreiro_linha in letreiros_alvo:
            for veiculo in linha.get('vs', []):
                registros_para_salvar.append((
                    timestamp_coleta,
                    veiculo.get('p'),
                    letreiro_linha,
                    veiculo.get('py'),
                    veiculo.get('px'),
                    veiculo.get('ta')
                ))
    
    logging.info(f"API retornou {total_veiculos_api} veículos. Após o filtro, {len(registros_para_salvar)} serão salvos.")

    if not registros_para_salvar:
        logging.warning("Nenhum registro de posição para as linhas alvo. Nada a salvar.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO posicoes (timestamp_coleta, id_onibus, letreiro_linha, latitude, longitude, timestamp_posicao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, registros_para_salvar)
        conn.commit()
        conn.close()
        logging.info(f"{len(registros_para_salvar)} novos registros de POSIÇÃO foram salvos no banco de dados.")
    except sqlite3.Error as e:
        logging.error(f"Ocorreu um erro ao salvar os dados de posição no SQLite: {e}")

# --- Execução Principal ---
def main():
    logging.info("Serviço de coleta de POSIÇÕES da SPTrans (com filtro) iniciado.")
    try:
        # Carrega a configuração e prepara o filtro uma vez no início
        config = get_config()
        linhas_alvo_ids = get_linhas_alvo_ids(config)
        letreiros_alvo = get_letreiros_alvo(linhas_alvo_ids)
    except (FileNotFoundError, KeyError) as e:
        logging.error(f"Erro fatal ao carregar a configuração do filtro: {e}")
        return

    # Passamos a usar uma função lambda para que o schedule possa chamar o job com o argumento necessário
    schedule.every(30).minutes.do(lambda: job(letreiros_alvo))
    logging.info("Coleta de posições agendada para verificação a cada 30 minutos.")

    logging.info("Executando um ciclo de coleta inicial para teste...")
    job(letreiros_alvo)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
