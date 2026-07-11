"""
Assets Dagster para coleta de dados da API Olho Vivo SPTrans.

Envolve as funções existentes em src/coleta_sptrans.py e src/coleta_previsoes.py
sem modificá-las — o asset chama as funções originais que já abrem conexão,
autenticam e escrevem no SQLite.
"""

import logging
import os
import sys

import requests
from dagster import MetadataValue, Output, asset

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import coleta_previsoes, coleta_sptrans
from src.database import get_db_path, registrar_linhagem

logger = logging.getLogger(__name__)


def _contagem_tabela(tabela: str) -> int:
    """Retorna row_count de uma tabela SQLite (0 se tabela vazia ou não existir)."""
    try:
        import sqlite3

        path = get_db_path()
        if not os.path.exists(path):
            return 0
        conn = sqlite3.connect(path)
        try:
            row = conn.execute(f"SELECT count(*) FROM {tabela}").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


@asset(
    group_name="coleta",
    description=(
        "Coleta posições de GPS dos ônibus das linhas alvo via API Olho Vivo "
        "e persiste em data/sptrans_data.db (tabela posicoes)."
    ),
)
def posicoes_sptrans() -> Output[int]:
    """Executa um ciclo de coleta de posições."""
    config = coleta_sptrans.get_config()
    linhas_alvo_ids = coleta_sptrans.get_linhas_alvo_ids(config)
    letreiros_alvo = coleta_sptrans.get_letreiros_alvo(linhas_alvo_ids)
    coleta_sptrans.job(letreiros_alvo)

    row_count = _contagem_tabela("posicoes")
    registrar_linhagem("posicoes_sptrans", "posicoes", "bronze", row_count, "ok")

    logger.info("Asset posicoes_sptrans materializado com sucesso (%s registros).", row_count)
    return Output(
        row_count,
        metadata={
            "table": MetadataValue.text("posicoes"),
            "layer": MetadataValue.text("bronze"),
            "row_count": MetadataValue.int(row_count),
            "db_path": MetadataValue.text(get_db_path()),
        },
    )


@asset(
    group_name="coleta",
    description=(
        "Coleta previsões de chegada para todas as linhas alvo via API Olho Vivo "
        "e persiste em data/sptrans_data.db (tabela previsoes)."
    ),
)
def previsoes_sptrans() -> Output[int]:
    """Executa um ciclo de coleta de previsões."""
    config = coleta_previsoes.get_config()
    token = coleta_previsoes.get_token(config)
    linhas_alvo = coleta_previsoes.get_linhas_alvo(config)
    session = requests.Session()
    if coleta_previsoes.autenticar(token, session):
        coleta_previsoes.job(session, linhas_alvo)
        logger.info("Asset previsoes_sptrans materializado com sucesso.")
    else:
        logger.error("Falha na autenticação — pulando coleta de previsões.")

    row_count = _contagem_tabela("previsoes")
    registrar_linhagem("previsoes_sptrans", "previsoes", "bronze", row_count, "ok")

    logger.info("Asset previsoes_sptrans: %s registros em previsoes.", row_count)
    return Output(
        row_count,
        metadata={
            "table": MetadataValue.text("previsoes"),
            "layer": MetadataValue.text("bronze"),
            "row_count": MetadataValue.int(row_count),
            "db_path": MetadataValue.text(get_db_path()),
        },
    )
