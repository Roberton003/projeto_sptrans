import os
import sqlite3
import logging
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_PATH = os.path.join('data', 'sptrans_data.db')

# Limites para os alertas (em minutos)
LIMITE_DADOS_ANTIGOS = 60

# --- Funções de Verificação (Health Checks) ---

def verificar_dados_velhos(conn, problemas):
    """Verifica se os dados nas tabelas não são mais antigos que o limite definido."""
    logging.info("Verificando se há dados antigos...")
    cursor = conn.cursor()
    tabelas = ['posicoes', 'previsoes']
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT MAX(timestamp_coleta) FROM {tabela}")
            ultimo_timestamp_str = cursor.fetchone()[0]
            if ultimo_timestamp_str:
                ultimo_timestamp = datetime.fromisoformat(ultimo_timestamp_str)
                diferenca = datetime.now() - ultimo_timestamp
                if diferenca.total_seconds() > LIMITE_DADOS_ANTIGOS * 60:
                    problemas.append(f"ALERTA: A tabela '{tabela}' não recebe dados novos há mais de {LIMITE_DADOS_ANTIGOS} minutos.")
            else:
                problemas.append(f"ALERTA: A tabela '{tabela}' está vazia.")
        except sqlite3.Error as e:
            problemas.append(f"ERRO: Não foi possível verificar a tabela '{tabela}': {e}")

def verificar_lotes_vazios(conn, problemas):
    """Verifica se o último lote de coleta inserido no banco está vazio."""
    logging.info("Verificando se houve lotes de coleta vazios...")
    cursor = conn.cursor()
    tabelas = ['posicoes', 'previsoes']
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE timestamp_coleta = (SELECT MAX(timestamp_coleta) FROM {tabela})")
            contagem = cursor.fetchone()[0]
            if contagem == 0:
                problemas.append(f"ALERTA: O último lote de coleta para a tabela '{tabela}' foi vazio.")
        except sqlite3.Error as e:
            problemas.append(f"ERRO: Não foi possível verificar o último lote da tabela '{tabela}': {e}")

# --- Função de Alerta ---

def enviar_alerta_email(problemas):
    """Envia um e-mail de alerta com a lista de problemas encontrados."""
    logging.info("Enviando e-mail de alerta...")
    try:
        # Lê as configurações de e-mail das variáveis de ambiente para segurança
        EMAIL_HOST = os.environ.get('EMAIL_HOST')
        EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
        EMAIL_USER = os.environ.get('EMAIL_USER')
        EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
        EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT')

        if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
            logging.error("Variáveis de ambiente para envio de e-mail não configuradas. Não é possível enviar alerta.")
            return

        # Cria a mensagem do e-mail
        msg = EmailMessage()
        msg['Subject'] = "[ALERTA] Problema na Pipeline de Dados SPTrans"
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECIPIENT
        
        corpo_email = "Os seguintes problemas foram detectados na pipeline de dados:\n\n" + "\n".join(f"- {p}" for p in problemas)
        msg.set_content(corpo_email)

        # Conecta ao servidor SMTP e envia o e-mail
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASSWORD)
            s.send_message(msg)
        
        logging.info("E-mail de alerta enviado com sucesso!")

    except Exception as e:
        logging.error(f"Falha ao enviar e-mail de alerta: {e}")

# --- Função Principal ---
def main():
    """Orquestra a execução das verificações e o envio de alertas."""
    logging.info("--- Iniciando Robô Fiscal ---")
    problemas_encontrados = []
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        verificar_dados_velhos(conn, problemas_encontrados)
        verificar_lotes_vazios(conn, problemas_encontrados)
    except sqlite3.Error as e:
        problemas_encontrados.append(f"Falha crítica ao conectar ou ler o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

    if problemas_encontrados:
        logging.warning(f"Problemas encontrados na pipeline: {problemas_encontrados}")
        enviar_alerta_email(problemas_encontrados)
    else:
        logging.info("Pipeline de dados está saudável. Nenhum problema encontrado.")

    logging.info("--- Robô Fiscal Finalizado ---")

if __name__ == "__main__":
    main()
