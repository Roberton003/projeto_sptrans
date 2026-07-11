"""Testes para inicializar_banco.py — schema e índices UNIQUE."""

import os
import sqlite3
import tempfile

from src.inicializar_banco import SQL_CREATE_POSICOES, SQL_CREATE_PREVISOES


def _get_table_names(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def _get_index_names(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    return {row[0] for row in cursor.fetchall()}


def test_schema_creation():
    """Verifica que as tabelas e índices UNIQUE são criados corretamente."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute(SQL_CREATE_POSICOES)
        cursor.execute(SQL_CREATE_PREVISOES)

        # Índices UNIQUE (simula o que inicializar_banco.main() faz)
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup "
            "ON posicoes(timestamp_coleta, id_onibus)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_previsoes_dedup "
            "ON previsoes(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)"
        )

        tables = _get_table_names(cursor)
        assert "posicoes" in tables
        assert "previsoes" in tables

        indexes = _get_index_names(cursor)
        assert "idx_posicoes_dedup" in indexes
        assert "idx_previsoes_dedup" in indexes

        conn.close()
    finally:
        os.unlink(path)


def test_schema_idempotent():
    """Executar CREATE TABLE + INDEX duas vezes não causa erro."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        for _ in range(2):
            cursor.execute(SQL_CREATE_POSICOES)
            cursor.execute(SQL_CREATE_PREVISOES)
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup "
                "ON posicoes(timestamp_coleta, id_onibus)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_previsoes_dedup "
                "ON previsoes(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)"
            )

        tables = _get_table_names(cursor)
        assert "posicoes" in tables
        assert "previsoes" in tables

        conn.close()
    finally:
        os.unlink(path)


def test_unique_index_enforced_posicoes():
    """INSERT duplicado em posicoes com mesma (timestamp_coleta, id_onibus) é rejeitado."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute(SQL_CREATE_POSICOES)
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup "
            "ON posicoes(timestamp_coleta, id_onibus)"
        )

        cursor.execute(
            "INSERT OR IGNORE INTO posicoes "
            "(timestamp_coleta, id_onibus, letreiro_linha, latitude, longitude) "
            "VALUES ('2025-08-15 10:00:00', 1001, '8000-10', -23.55, -46.63)"
        )
        cursor.execute(
            "INSERT OR IGNORE INTO posicoes "
            "(timestamp_coleta, id_onibus, letreiro_linha, latitude, longitude) "
            "VALUES ('2025-08-15 10:00:00', 1001, '8000-10', -23.55, -46.63)"
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM posicoes")
        count = cursor.fetchone()[0]
        assert count == 1, "UNIQUE INDEX deveria impedir duplicatas"

        conn.close()
    finally:
        os.unlink(path)
