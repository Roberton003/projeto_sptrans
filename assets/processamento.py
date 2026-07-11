"""
Assets Dagster para processamento pós-coleta: compactação Parquet e expurgo.

Envolve as funções de src/compactar_parquet.py e src/expurgar_sqlite.py
sem modificá-las.
"""

import logging
import os
import sys
from datetime import datetime, timedelta

import duckdb
from dagster import MetadataValue, Output, asset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import compactar_parquet, expurgar_sqlite
from src.database import get_connection, registrar_linhagem

logger = logging.getLogger(__name__)

JANELA_DIAS = 7


def _contagem_parquet(con: duckdb.DuckDBPyConnection, tabela: str) -> int:
    """Retorna row_count total do Parquet para uma tabela."""
    parquet_dir = os.path.join(compactar_parquet.PARQUET_DIR, tabela)
    if not os.path.exists(parquet_dir):
        return 0
    try:
        row = con.execute(f"SELECT count(*) FROM read_parquet('{parquet_dir}/**/*.parquet')").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


@asset(
    group_name="processamento",
    deps=["posicoes_sptrans"],
    description=(
        "Compacta dados de posições do SQLite para Parquet particionado por data "
        "(camada analítica). Idempotente por partição."
    ),
)
def compactar_posicoes() -> Output[int]:
    """Exporta posições do dia anterior para Parquet."""
    if not os.path.exists(compactar_parquet.DB_PATH):
        logger.warning("Banco não encontrado. Pulando compactação.")
        return Output(0, metadata={"row_count": MetadataValue.int(0), "status": MetadataValue.text("skipped")})

    data_alvo = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    con = duckdb.connect()
    try:
        total = compactar_parquet.exportar_tabela(con, "posicoes", filtro_data=data_alvo)
        if total:
            registrar_linhagem("compactar_posicoes", "posicoes", "silver", total, "ok")
        logger.info("compactar_posicoes: %s registros exportados para Parquet.", total)
    finally:
        con.close()

    return Output(
        total or 0,
        metadata={
            "table": MetadataValue.text("posicoes"),
            "layer": MetadataValue.text("silver"),
            "row_count": MetadataValue.int(total or 0),
            "partition": MetadataValue.text(data_alvo),
        },
    )


@asset(
    group_name="processamento",
    deps=["previsoes_sptrans"],
    description=(
        "Compacta dados de previsões do SQLite para Parquet particionado por data "
        "(camada analítica). Idempotente por partição."
    ),
)
def compactar_previsoes() -> Output[int]:
    """Exporta previsões do dia anterior para Parquet."""
    if not os.path.exists(compactar_parquet.DB_PATH):
        logger.warning("Banco não encontrado. Pulando compactação.")
        return Output(0, metadata={"row_count": MetadataValue.int(0), "status": MetadataValue.text("skipped")})

    data_alvo = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    con = duckdb.connect()
    try:
        total = compactar_parquet.exportar_tabela(con, "previsoes", filtro_data=data_alvo)
        if total:
            registrar_linhagem("compactar_previsoes", "previsoes", "silver", total, "ok")
        logger.info("compactar_previsoes: %s registros exportados para Parquet.", total)
    finally:
        con.close()

    return Output(
        total or 0,
        metadata={
            "table": MetadataValue.text("previsoes"),
            "layer": MetadataValue.text("silver"),
            "row_count": MetadataValue.int(total or 0),
            "partition": MetadataValue.text(data_alvo),
        },
    )


@asset(
    group_name="processamento",
    deps=["compactar_posicoes"],
    description=("Expurga posições com mais de N dias do SQLite (janela quente). O histórico permanece em Parquet."),
)
def expurgar_posicoes() -> Output[int]:
    """Remove posições antigas do banco (janela quente)."""
    if not os.path.exists(expurgar_sqlite.DB_PATH):
        logger.warning("Banco não encontrado. Pulando expurgo.")
        return Output(0, metadata={"row_count": MetadataValue.int(0), "status": MetadataValue.text("skipped")})

    limite = datetime.now() - timedelta(days=JANELA_DIAS)
    with get_connection() as conn:
        total = expurgar_sqlite.expurgar(conn, "posicoes", limite, dry_run=False)
        if total:
            registrar_linhagem("expurgar_posicoes", "posicoes", "bronze", total, "ok")
            logger.info("expurgar_posicoes: %s registros removidos.", total)

    return Output(
        total or 0,
        metadata={
            "table": MetadataValue.text("posicoes"),
            "action": MetadataValue.text("expurgo"),
            "rows_removed": MetadataValue.int(total or 0),
        },
    )


@asset(
    group_name="processamento",
    deps=["compactar_previsoes"],
    description=("Expurga previsões com mais de N dias do SQLite (janela quente). O histórico permanece em Parquet."),
)
def expurgar_previsoes() -> Output[int]:
    """Remove previsões antigas do banco (janela quente)."""
    if not os.path.exists(expurgar_sqlite.DB_PATH):
        logger.warning("Banco não encontrado. Pulando expurgo.")
        return Output(0, metadata={"row_count": MetadataValue.int(0), "status": MetadataValue.text("skipped")})

    limite = datetime.now() - timedelta(days=JANELA_DIAS)
    with get_connection() as conn:
        total = expurgar_sqlite.expurgar(conn, "previsoes", limite, dry_run=False)
        if total:
            registrar_linhagem("expurgar_previsoes", "previsoes", "bronze", total, "ok")
            logger.info("expurgar_previsoes: %s registros removidos.", total)

    return Output(
        total or 0,
        metadata={
            "table": MetadataValue.text("previsoes"),
            "action": MetadataValue.text("expurgo"),
            "rows_removed": MetadataValue.int(total or 0),
        },
    )
