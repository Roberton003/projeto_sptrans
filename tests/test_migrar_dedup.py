"""Testes para migrar_dedup.py — remoção de duplicatas e criação de UNIQUE INDEX."""

import os
import sqlite3
import tempfile

import pytest

from src.migrar_dedup import remover_duplicatas


def test_remover_duplicatas_posicoes():
    """Remove duplicatas mantendo o menor id, depois cria UNIQUE INDEX."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE posicoes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp_coleta DATETIME, "
            "id_onibus INTEGER"
            ")"
        )
        # Insere 3 registros, 2 deles duplicados
        cursor.execute(
            "INSERT INTO posicoes (timestamp_coleta, id_onibus) VALUES ('2025-08-15 10:00:00', 1001)"
        )  # id=1
        cursor.execute(
            "INSERT INTO posicoes (timestamp_coleta, id_onibus) VALUES ('2025-08-15 10:00:00', 1001)"
        )  # id=2 (dup)
        cursor.execute(
            "INSERT INTO posicoes (timestamp_coleta, id_onibus) VALUES ('2025-08-15 10:00:00', 1002)"
        )  # id=3
        conn.commit()

        remover_duplicatas(
            cursor, "posicoes", ["timestamp_coleta", "id_onibus"], "idx_posicoes_dedup"
        )
        conn.commit()

        cursor.execute("SELECT id, timestamp_coleta, id_onibus FROM posicoes ORDER BY id")
        restantes = cursor.fetchall()
        assert len(restantes) == 2, "Deveriam restar 2 registros após dedup"
        # id=1 (1001) e id=3 (1002), id=2 foi removido
        assert restantes[0][0] == 1
        assert restantes[1][0] == 3

        # Verifica UNIQUE INDEX
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO posicoes (timestamp_coleta, id_onibus) VALUES ('2025-08-15 10:00:00', 1001)"
            )
        conn.close()
    finally:
        os.unlink(path)
