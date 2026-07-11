"""Testes para compactar_parquet.py — exportação SQLite → Parquet."""

import os
import shutil
import tempfile

import duckdb
import pytest

import src.compactar_parquet as cp


@pytest.fixture
def temp_parquet_dir():
    """Diretório temporário para parquet."""
    path = tempfile.mkdtemp()
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)


def test_exportar_parquet_com_dados(temp_db_connection, temp_parquet_dir, temp_db_path):
    """Exporta dados do SQLite para Parquet e verifica conteúdo."""
    cursor = temp_db_connection.cursor()
    cursor.execute(
        "INSERT INTO posicoes (timestamp_coleta, id_onibus, letreiro_linha, latitude, longitude) "
        "VALUES ('2025-08-15 10:00:00', 1001, '8000-10', -23.55, -46.63)"
    )
    temp_db_connection.commit()
    temp_db_connection.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cp, "DB_PATH", temp_db_path)
        mp.setattr(cp, "PARQUET_DIR", temp_parquet_dir)

        con = duckdb.connect()
        count = None
        try:
            count = cp.exportar_tabela(con, "posicoes", filtro_data="2025-08-15")
        finally:
            con.close()

    assert count == 1, "Deveria exportar 1 registro"

    con2 = duckdb.connect()
    try:
        result = con2.execute(
            f"SELECT id_onibus, letreiro_linha "
            f"FROM read_parquet('{temp_parquet_dir}/posicoes/**/*.parquet')"
        ).fetchall()
        assert len(result) == 1
        assert result[0][0] == 1001
        assert result[0][1] == "8000-10"
    finally:
        con2.close()


def test_exportar_parquet_sem_dados(temp_db_connection, temp_parquet_dir, temp_db_path):
    """Exportar tabela vazia retorna 0."""
    temp_db_connection.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cp, "DB_PATH", temp_db_path)
        mp.setattr(cp, "PARQUET_DIR", temp_parquet_dir)

        con = duckdb.connect()
        try:
            count = cp.exportar_tabela(con, "posicoes", filtro_data="2025-08-15")
        finally:
            con.close()

    assert count == 0


def test_exportar_parquet_idempotente(temp_db_connection, temp_parquet_dir, temp_db_path):
    """Exportar 2× o mesmo dado produz mesmo conteúdo."""
    cursor = temp_db_connection.cursor()
    cursor.execute(
        "INSERT INTO posicoes (timestamp_coleta, id_onibus, letreiro_linha, latitude, longitude) "
        "VALUES ('2025-08-15 10:00:00', 1001, '8000-10', -23.55, -46.63)"
    )
    temp_db_connection.commit()
    temp_db_connection.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cp, "DB_PATH", temp_db_path)
        mp.setattr(cp, "PARQUET_DIR", temp_parquet_dir)

        con = duckdb.connect()
        try:
            count1 = cp.exportar_tabela(con, "posicoes", filtro_data="2025-08-15")
            count2 = cp.exportar_tabela(con, "posicoes", filtro_data="2025-08-15")
        finally:
            con.close()

    assert count1 == count2 == 1

    con3 = duckdb.connect()
    try:
        total = con3.execute(
            f"SELECT count(*) FROM read_parquet('{temp_parquet_dir}/posicoes/**/*.parquet')"
        ).fetchone()[0]
    finally:
        con3.close()

    assert total == 1, "Idempotência: mesma contagem após 2 exportações"
