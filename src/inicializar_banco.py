"""
Inicialização do banco de dados — SQLite (padrão) ou PostgreSQL (DATABASE_URL).

Cria as tabelas e índices UNIQUE necessários para o pipeline.

Uso:
    python src/inicializar_banco.py                      # SQLite (padrão)
    DATABASE_URL=postgresql://... python src/inicializar_banco.py  # PostgreSQL
"""

import logging
import os

from src.database import get_connection, schema_sql

# Constantes exportadas para testes (backward compat)
SQL_CREATE_POSICOES, SQL_CREATE_PREVISOES, _ = schema_sql()[0][:3]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DB_PATH = os.path.join("data", "sptrans_data.db")


def main():
    """Cria o banco de dados e as tabelas."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        logging.info(f"Inicializando banco PostgreSQL: {db_url}")
    else:
        logging.info(f"Verificando e inicializando o banco SQLite em: {DB_PATH}")

    tables, indexes = schema_sql()

    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with get_connection() as conn:
            cursor = conn.cursor()

            logging.info("Criando tabelas...")
            for sql in tables:
                cursor.execute(sql)

            logging.info("Criando índices de deduplicação (UNIQUE)...")
            for sql in indexes:
                cursor.execute(sql)

        logging.info("Banco de dados verificado e pronto para uso!")

    except Exception as e:
        logging.error(f"Ocorreu um erro ao inicializar o banco: {e}")


if __name__ == "__main__":
    main()
