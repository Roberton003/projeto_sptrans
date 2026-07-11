"""Testes para expurgar_sqlite.py — expurgo da janela quente."""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

from src.expurgar_sqlite import expurgar


def test_expurgar_sem_registros():
    """Expurgo com tabela vazia não quebra."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE posicoes (id INTEGER PRIMARY KEY, timestamp_coleta DATETIME)")
        conn.commit()

        limite = datetime.now()
        result = expurgar(conn, "posicoes", limite)
        assert result == 0
        conn.close()
    finally:
        os.unlink(path)


def test_expurgar_dry_run():
    """Dry-run não remove registros."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE posicoes (id INTEGER PRIMARY KEY, timestamp_coleta DATETIME)")
        cursor.execute("INSERT INTO posicoes VALUES (1, '2024-01-01')")
        conn.commit()

        limite = datetime.now()
        result = expurgar(conn, "posicoes", limite, dry_run=True)
        assert result == 1, "Dry-run deveria reportar 1 registro"

        cursor.execute("SELECT COUNT(*) FROM posicoes")
        assert cursor.fetchone()[0] == 1, "Dry-run não deveria remover registros"
        conn.close()
    finally:
        os.unlink(path)


def test_expurgar_executa():
    """Expurgo real remove registros antigos."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE posicoes (id INTEGER PRIMARY KEY, timestamp_coleta DATETIME)")
        # Um registro antigo e um recente
        cursor.execute("INSERT INTO posicoes VALUES (1, '2024-01-01')")
        cursor.execute("INSERT INTO posicoes VALUES (2, ?)", (datetime.now().isoformat(),))
        conn.commit()

        limite = datetime.now() - timedelta(days=1)
        result = expurgar(conn, "posicoes", limite)
        assert result == 1, "Deveria expurgar 1 registro"

        cursor.execute("SELECT id FROM posicoes")
        restantes = [row[0] for row in cursor.fetchall()]
        assert restantes == [2], "Deveria manter apenas o registro recente"
        conn.close()
    finally:
        os.unlink(path)


def test_expurgar_duas_tabelas():
    """Expurgo em duas tabelas funciona independentemente."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        for tabela in ("posicoes", "previsoes"):
            cursor.execute(
                f"CREATE TABLE {tabela} (id INTEGER PRIMARY KEY, timestamp_coleta DATETIME)"
            )
            cursor.execute(f"INSERT INTO {tabela} VALUES (1, '2024-01-01')")
            cursor.execute(f"INSERT INTO {tabela} VALUES (2, ?)", (datetime.now().isoformat(),))
        conn.commit()

        limite = datetime.now() - timedelta(days=1)
        total = 0
        for tabela in ("posicoes", "previsoes"):
            total += expurgar(conn, tabela, limite)
        assert total == 2
        conn.close()
    finally:
        os.unlink(path)
