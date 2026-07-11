"""
Abstração de banco de dados — SQLite (local) ou PostgreSQL (DATABASE_URL).

Uso:
    from src.database import get_connection, insert_sql, registrar_linhagem, DB_PATH

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(insert_sql("posicoes", columns), rows)

    # Registrar linhagem pós-coleta
    registrar_linhagem("posicoes_sptrans", "posicoes", "bronze", 1000, "ok")

Modo SQLite (padrão):
    Banco em data/sptrans_data.db, INSERT OR IGNORE, placeholders ?

Modo PostgreSQL:
    Define DATABASE_URL=postgresql://user:pass@host/db
    INSERT ... ON CONFLICT DO NOTHING, placeholders %s
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")
SQLITE_PATH = os.path.join("data", "sptrans_data.db")
DB_PATH = SQLITE_PATH  # alias para compatibilidade com módulos existentes
IS_POSTGRES = DATABASE_URL is not None

logger = logging.getLogger(__name__)


def get_db_path():
    """Caminho do SQLite (para DuckDB sqlite_scan e os.path.exists)."""
    return SQLITE_PATH


@contextmanager
def get_connection():
    """Retorna conexão DB-API2: SQLite (padrão) ou PostgreSQL (se DATABASE_URL).

    Uso:
        with get_connection() as conn:
            conn.execute(...)
        # commit automático no final; rollback em exceção
    """
    if IS_POSTGRES:
        import psycopg2

        conn = psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def schema_sql():
    """Retorna tupla (create_sql_list, index_sql_list) adequada ao backend."""
    if IS_POSTGRES:
        return _schema_postgres()
    return _schema_sqlite()


def _linhagem_table_sql():
    """SQL para tabela de auditoria de linhagem (backend-agnóstico, placeholders compatíveis)."""
    return """
    CREATE TABLE IF NOT EXISTS lineage_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT NOT NULL,
        table_name TEXT NOT NULL,
        layer TEXT NOT NULL,
        run_timestamp DATETIME NOT NULL,
        row_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ok'
    )
    """


def registrar_linhagem(asset_name: str, table_name: str, layer: str, row_count: int, status: str = "ok") -> None:
    """Regista metadata de linhagem no banco (tabela lineage_audit).

    Args:
        asset_name: Nome do asset Dagster (ex: "posicoes_sptrans").
        table_name: Nome da tabela física (ex: "posicoes").
        layer: "bronze" | "silver" | "gold".
        row_count: Número de registros.
        status: "ok" | "falha" | "alerta".
    """
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO lineage_audit (asset_name, table_name, layer, run_timestamp, row_count, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (asset_name, table_name, layer, datetime.now().isoformat(), row_count, status),
            )
        logger.debug("Linhagem registrada: %s/%s (%s, %s registros)", layer, table_name, asset_name, row_count)
    except Exception:
        logger.warning("Falha ao registrar linhagem (banco pode não estar inicializado): %s/%s", layer, table_name)


def _schema_sqlite():
    """Schema SQLite."""
    tables = [
        """
        CREATE TABLE IF NOT EXISTS posicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_coleta DATETIME NOT NULL,
            id_onibus INTEGER NOT NULL,
            letreiro_linha TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timestamp_posicao DATETIME
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS previsoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_coleta DATETIME NOT NULL,
            id_linha INTEGER NOT NULL,
            id_onibus INTEGER NOT NULL,
            id_parada INTEGER,
            horario_previsao TEXT
        )
        """,
        """
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
        )
        """,
    ]
    indexes = [
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup
        ON posicoes(timestamp_coleta, id_onibus)
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_previsoes_dedup
        ON previsoes(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)
        """,
    ]
    # Tabela de auditoria (linhagem) adicionada ao schema
    audit_table = _linhagem_table_sql()
    tables.append(audit_table)
    return tables, indexes


def _schema_postgres():
    """Schema PostgreSQL (sintaxe compatível com PostgreSQL 16)."""
    tables = [
        """
        CREATE TABLE IF NOT EXISTS posicoes (
            id SERIAL PRIMARY KEY,
            timestamp_coleta TIMESTAMP NOT NULL,
            id_onibus INTEGER NOT NULL,
            letreiro_linha TEXT,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            timestamp_posicao TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS previsoes (
            id SERIAL PRIMARY KEY,
            timestamp_coleta TIMESTAMP NOT NULL,
            id_linha INTEGER NOT NULL,
            id_onibus INTEGER NOT NULL,
            id_parada INTEGER,
            horario_previsao TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS resultados_analise (
            id SERIAL PRIMARY KEY,
            timestamp_analise TIMESTAMP NOT NULL,
            id_onibus INTEGER NOT NULL,
            letreiro_linha TEXT,
            posicao_atual_lat DOUBLE PRECISION,
            posicao_atual_lon DOUBLE PRECISION,
            horario_posicao TIMESTAMP,
            proximo_ponto_previsto TEXT,
            horario_previsto_chegada TEXT
        )
        """,
    ]
    # Tabela de auditoria (linhagem) para PostgreSQL
    tables.append("""
        CREATE TABLE IF NOT EXISTS lineage_audit (
            id SERIAL PRIMARY KEY,
            asset_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            layer TEXT NOT NULL,
            run_timestamp TIMESTAMP NOT NULL,
            row_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ok'
        )
    """)
    indexes = [
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup
        ON posicoes(timestamp_coleta, id_onibus)
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_previsoes_dedup
        ON previsoes(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)
        """,
    ]
    return tables, indexes


def insert_sql(table, columns, or_ignore=True):
    """Gera SQL INSERT com tratamento de conflito adequado ao backend.

    Args:
        table: Nome da tabela.
        columns: Lista de nomes de colunas.
        or_ignore: Se True, usa INSERT OR IGNORE (SQLite) ou
                   ON CONFLICT DO NOTHING (PostgreSQL).

    Retorna:
        String SQL com placeholders no formato correto.
    """
    cols = ", ".join(columns)
    ph = ", ".join(["?" if not IS_POSTGRES else "%s"] * len(columns))

    if or_ignore:
        if IS_POSTGRES:
            return f"INSERT INTO {table} ({cols}) VALUES ({ph}) ON CONFLICT DO NOTHING"
        else:
            return f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({ph})"
    return f"INSERT INTO {table} ({cols}) VALUES ({ph})"
