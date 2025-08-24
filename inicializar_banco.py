import sqlite3
import os
import logging

# --- Configuração ---
DB_PATH = os.path.join('data', 'sptrans_data.db')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Schema do Banco de Dados ---
# Usamos a sintaxe do SQLite para criar as tabelas.
# 'IF NOT EXISTS' garante que não teremos um erro se o script for executado mais de uma vez.

SQL_CREATE_POSICOES = """
CREATE TABLE IF NOT EXISTS posicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_coleta DATETIME NOT NULL,
    id_onibus INTEGER NOT NULL,
    letreiro_linha TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timestamp_posicao DATETIME
);
"""

SQL_CREATE_PREVISOES = """
CREATE TABLE IF NOT EXISTS previsoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_coleta DATETIME NOT NULL,
    id_linha INTEGER NOT NULL,
    id_onibus INTEGER NOT NULL,
    id_parada INTEGER,
    horario_previsao TEXT
);
"""

# Adicionamos a planta da nossa nova tabela de resultados
SQL_CREATE_RESULTADOS = """
CREATE TABLE IF NOT EXISTS resultados_analise (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_analise DATETIME NOT NULL,
    id_onibus INTEGER NOT NULL,
    letreiro_linha TEXT,
    posicao_atual_lat REAL,
    posicao_atual_lon REAL,
    horario_posicao DATETIME,
    proximo_ponto_previsto TEXT,
    horario_previsto_chegada TEXT
);
"""

# --- Função Principal ---
def main():
    """Cria o banco de dados e as tabelas."""
    logging.info(f"Verificando e inicializando o banco de dados em: {DB_PATH}")

    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        logging.info("Verificando tabela 'posicoes'...")
        cursor.execute(SQL_CREATE_POSICOES)
        
        logging.info("Verificando tabela 'previsoes'...")
        cursor.execute(SQL_CREATE_PREVISOES)

        logging.info("Verificando tabela 'resultados_analise'...")
        cursor.execute(SQL_CREATE_RESULTADOS)

        conn.commit()
        conn.close()

        logging.info("Banco de dados verificado e pronto para uso!")

    except sqlite3.Error as e:
        logging.error(f"Ocorreu um erro com o SQLite: {e}")
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()