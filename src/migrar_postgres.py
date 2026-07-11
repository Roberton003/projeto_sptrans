"""
Migração one-shot: SQLite → PostgreSQL.

Copia todos os dados do SQLite local (data/sptrans_data.db) para o PostgreSQL
configurado em DATABASE_URL. Idempotente: pode ser executado múltiplas vezes
sem duplicar registros (usa ON CONFLICT DO NOTHING).

Uso:
    DATABASE_URL=postgresql://sptrans:sptrans_local@localhost:5432/sptrans \\
        python src/migrar_postgres.py

Pré-requisitos:
    - PostgreSQL rodando (docker compose up postgres)
    - DATABASE_URL configurada
    - src/inicializar_banco.py já executado contra o PostgreSQL
"""

import logging
import os
import sqlite3

import psycopg2

from src.database import DATABASE_URL, SQLITE_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TABELAS = {
    "posicoes": [
        "timestamp_coleta",
        "id_onibus",
        "letreiro_linha",
        "latitude",
        "longitude",
        "timestamp_posicao",
    ],
    "previsoes": [
        "timestamp_coleta",
        "id_linha",
        "id_onibus",
        "id_parada",
        "horario_previsao",
    ],
}


def migrar():
    """Executa a migração completa SQLite → PostgreSQL."""
    if not DATABASE_URL:
        logging.error("DATABASE_URL não configurada. Abortando.")
        return

    if not os.path.exists(SQLITE_PATH):
        logging.error(f"SQLite não encontrado em {SQLITE_PATH}. Abortando.")
        return

    logging.info(f"Origem: SQLite ({SQLITE_PATH})")
    logging.info(f"Destino: PostgreSQL ({DATABASE_URL})")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cursor = pg_conn.cursor()

    try:
        for tabela, colunas in TABELAS.items():
            cols_sql = ", ".join(colunas)
            ph = ", ".join(["%s"] * len(colunas))
            insert_sql = f"INSERT INTO {tabela} ({cols_sql}) VALUES ({ph}) ON CONFLICT DO NOTHING"

            # Lê do SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT {cols_sql} FROM {tabela}")
            rows = sqlite_cursor.fetchall()
            sqlite_cursor.close()

            if not rows:
                logging.info(f"  '{tabela}': 0 registros (vazio). Pulando.")
                continue

            # Insere no PostgreSQL em lotes
            BATCH = 1000
            total = 0
            for i in range(0, len(rows), BATCH):
                batch = rows[i : i + BATCH]
                pg_cursor.executemany(insert_sql, batch)
                pg_conn.commit()
                total += len(batch)
                logging.info(f"  '{tabela}': {total}/{len(rows)} registros migrados...")

            # Verificação
            pg_cursor.execute(f"SELECT count(*) FROM {tabela}")
            pg_count = pg_cursor.fetchone()[0]
            logging.info(f"  '{tabela}': migração concluída. SQLite: {len(rows)} | PostgreSQL: {pg_count}")

        logging.info("Migração SQLite → PostgreSQL concluída com sucesso!")

    except Exception as e:
        pg_conn.rollback()
        logging.error(f"Erro durante a migração: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrar()
