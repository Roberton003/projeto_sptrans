"""Fixtures compartilhadas para os testes."""

import os
import sqlite3
import tempfile

import pandas as pd
import pytest


@pytest.fixture
def sample_posicoes_df():
    """DataFrame de exemplo com dados de posição."""
    return pd.DataFrame(
        {
            "timestamp_coleta": pd.to_datetime(["2025-08-15 10:00:00", "2025-08-15 10:00:00"]),
            "id_onibus": [1001, 1002],
            "letreiro_linha": ["8000-10", "8000-10"],
            "latitude": [-23.5505, -23.5510],
            "longitude": [-46.6333, -46.6328],
            "timestamp_posicao": pd.to_datetime(["2025-08-15 09:59:00", "2025-08-15 09:58:00"]),
        }
    )


@pytest.fixture
def sample_previsoes_df():
    """DataFrame de exemplo com dados de previsão."""
    return pd.DataFrame(
        {
            "timestamp_coleta": pd.to_datetime(["2025-08-15 10:00:00", "2025-08-15 10:00:00"]),
            "id_linha": [2411, 2411],
            "id_onibus": [1001, 1002],
            "id_parada": [5001, 5002],
            "horario_previsao": pd.to_datetime(["2025-08-15 10:15:00", "2025-08-15 10:12:00"]),
        }
    )


@pytest.fixture
def temp_db_path():
    """Caminho para banco SQLite temporário."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_db_connection(temp_db_path):
    """SQLite connection para banco temporário já com schema."""
    _create_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    yield conn
    conn.close()


def _create_schema(db_path):
    """Cria schema completo (tabelas + índices UNIQUE) em db_path."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_coleta DATETIME NOT NULL,
            id_onibus INTEGER NOT NULL,
            letreiro_linha TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timestamp_posicao DATETIME
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS previsoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_coleta DATETIME NOT NULL,
            id_linha INTEGER NOT NULL,
            id_onibus INTEGER NOT NULL,
            id_parada INTEGER,
            horario_previsao TEXT
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup
        ON posicoes(timestamp_coleta, id_onibus)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_previsoes_dedup
        ON previsoes(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)
    """)
    conn.commit()
    conn.close()
