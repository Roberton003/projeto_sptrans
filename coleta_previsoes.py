import requests
import json
import configparser
import os
import logging
import time
import sqlite3
from datetime import datetime

# --- Configuração de Logging ---
LOG_FILE = 'coleta_previsoes.log'
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
DB_PATH = os.path.join('data', 'sptrans_data.db') # Caminho para o nosso novo banco de dados
INTERVALO_COLETA_SEGUNDOS = 300 # 5 minutos

# --- Funções de Configuração ---
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

def get_linhas_alvo(config):
    try:
        linhas_str = config['COLETA']['LINHAS_ALVO']
        linhas = [int(x.strip()) for x in linhas_str.split(',')]
        logging.info(f"Linhas alvo carregadas da configuração: {linhas}")
        return linhas
    except (KeyError, ValueError) as e:
        logging.error(f"Erro ao ler ou processar as linhas alvo do config.ini: {e}")
        return []

# --- Funções da API ---
def autenticar(token, session):
    url = f"{BASE_URL}/Login/Autenticar?token={token}"
    try:
        resp = session.post(url, timeout=10)
        resp.raise_for_status()
        return resp.json() is True
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de conexão durante a autenticação: {e}")
        return False

def coletar_previsao_linha(session, codigo_linha):
    url = f"{BASE_URL}/Previsao/Linha?codigoLinha={codigo_linha}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de conexão ao coletar previsões para a linha {codigo_linha}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar a resposta JSON da API para a linha {codigo_linha}.")
        return None

# --- Job de Coleta e Armazenamento no Banco de Dados ---
def job(session, linhas_alvo):
    """Coleta dados para as linhas alvo e os insere no banco de dados SQLite."""
    if not linhas_alvo:
        logging.warning("Nenhuma linha alvo configurada. Pulando ciclo de coleta.")
        return

    timestamp_coleta = datetime.now()
    registros_para_salvar = []

    for linha_id in linhas_alvo:
        logging.info(f"Coletando previsões para a linha: {linha_id}")
        dados = coletar_previsao_linha(session, linha_id)
        if not dados or not dados.get('ps'):
            logging.warning(f'Nenhum dado de previsão foi coletado para a linha {linha_id}.')
            continue
        
        # Processa os dados para inserção no banco
        for ponto in dados['ps']:
            id_parada = ponto.get('cp')
            for veiculo in ponto.get('vs', []):
                registros_para_salvar.append((
                    timestamp_coleta,
                    linha_id,
                    veiculo.get('p'),
                    id_parada,
                    veiculo.get('t')
                ))

    if not registros_para_salvar:
        logging.warning("Nenhum registro de previsão para salvar no banco de dados neste ciclo.")
        return

    # Conecta ao banco e insere os dados
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO previsoes (timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)
            VALUES (?, ?, ?, ?, ?)
        """, registros_para_salvar)
        conn.commit()
        conn.close()
        logging.info(f"{len(registros_para_salvar)} novos registros de previsão foram salvos no banco de dados.")
    except sqlite3.Error as e:
        logging.error(f"Ocorreu um erro ao salvar os dados no SQLite: {e}")

# --- Execução Principal ---
def main():
    logging.info(f"Iniciando serviço de coleta de previsões. Intervalo: {INTERVALO_COLETA_SEGUNDOS} segundos.")
    try:
        config = get_config()
        token = get_token(config)
        linhas_alvo = get_linhas_alvo(config)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logging.error(f"Erro fatal de configuração: {e}")
        return

    session = requests.Session()

    while True:
        if not autenticar(token, session):
            logging.error('Falha na autenticação. Tentando novamente em 60 segundos.')
            time.sleep(60)
            continue
        
        job(session, linhas_alvo)
        
        logging.info(f"Ciclo de coleta finalizado. Aguardando {INTERVALO_COLETA_SEGUNDOS} segundos.")
        time.sleep(INTERVALO_COLETA_SEGUNDOS)

if __name__ == "__main__":
    main()
