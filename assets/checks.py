"""
Asset checks de qualidade para verificação entre camadas.

Cada check verifica a integridade entre Bronze (SQLite) e Silver (Parquet):
- Reconciliação de contagem de registros
- Tolerância configurável (padrão 5%)

Uso:
    Os checks são registrados em assets/__init__.py via Definitions(asset_checks=[...]).
"""

import logging
import os

import duckdb
from dagster import AssetCheckResult, AssetCheckSeverity, asset_check

# O decorator @asset_check em Dagster 1.13 não aceita severity;
# a severidade é definida em AssetCheckResult no retorno.
from src import compactar_parquet

logger = logging.getLogger(__name__)

TOLERANCIA_PCT = 5  # diferença percentual máxima aceitável


def _contagem_sqlite(tabela: str) -> int:
    """Contagem de registros no SQLite para uma tabela."""
    path = compactar_parquet.DB_PATH
    if not os.path.exists(path):
        return 0
    import sqlite3

    conn = sqlite3.connect(path)
    try:
        row = conn.execute(f"SELECT count(*) FROM {tabela}").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def _contagem_parquet(tabela: str) -> int:
    """Contagem de registros no Parquet para uma tabela."""
    parquet_dir = os.path.join(compactar_parquet.PARQUET_DIR, tabela)
    if not os.path.exists(parquet_dir):
        return 0
    con = duckdb.connect()
    try:
        row = con.execute(f"SELECT count(*) FROM read_parquet('{parquet_dir}/**/*.parquet')").fetchone()
        return row[0] if row else 0
    finally:
        con.close()


@asset_check(
    asset="compactar_posicoes",
    description="Verifica se a contagem de posições no Parquet (Silver) é consistente com o SQLite (Bronze).",
)
def check_posicoes_bronze_silver() -> AssetCheckResult:
    """Reconcilia contagem de posições entre Bronze (SQLite) e Silver (Parquet)."""
    bronze = _contagem_sqlite("posicoes")
    silver = _contagem_parquet("posicoes")

    if bronze == 0 and silver == 0:
        return AssetCheckResult(passed=True, description="Nenhum registro encontrado em ambas as camadas.")

    if bronze > 0:
        diff_pct = abs(bronze - silver) / bronze * 100
    else:
        diff_pct = 100.0 if silver > 0 else 0.0

    if diff_pct > TOLERANCIA_PCT:
        logger.warning(
            "CHECK FAIL: posicoes Bronze=%s Silver=%s (dif=%.1f%% > %s%%)",
            bronze,
            silver,
            diff_pct,
            TOLERANCIA_PCT,
        )
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description=(
                f"Diferença de {diff_pct:.1f}% entre Bronze ({bronze}) "
                f"e Silver ({silver}) — tolerância: {TOLERANCIA_PCT}%"
            ),
            metadata={
                "bronze_count": bronze,
                "silver_count": silver,
                "diff_pct": round(diff_pct, 1),
            },
        )

    logger.info("CHECK OK: posicoes Bronze=%s Silver=%s (dif=%.1f%%)", bronze, silver, diff_pct)
    return AssetCheckResult(
        passed=True,
        description=(
            f"Bronze ({bronze}) ↔ Silver ({silver}) — diferença de {diff_pct:.1f}% (tolerância: {TOLERANCIA_PCT}%)"
        ),
        metadata={
            "bronze_count": bronze,
            "silver_count": silver,
            "diff_pct": round(diff_pct, 1),
        },
    )


@asset_check(
    asset="compactar_previsoes",
    description="Verifica se a contagem de previsões no Parquet (Silver) é consistente com o SQLite (Bronze).",
)
def check_previsoes_bronze_silver() -> AssetCheckResult:
    """Reconcilia contagem de previsões entre Bronze (SQLite) e Silver (Parquet)."""
    bronze = _contagem_sqlite("previsoes")
    silver = _contagem_parquet("previsoes")

    if bronze == 0 and silver == 0:
        return AssetCheckResult(passed=True, description="Nenhum registro encontrado em ambas as camadas.")

    if bronze > 0:
        diff_pct = abs(bronze - silver) / bronze * 100
    else:
        diff_pct = 100.0 if silver > 0 else 0.0

    if diff_pct > TOLERANCIA_PCT:
        logger.warning(
            "CHECK FAIL: previsoes Bronze=%s Silver=%s (dif=%.1f%% > %s%%)",
            bronze,
            silver,
            diff_pct,
            TOLERANCIA_PCT,
        )
        return AssetCheckResult(
            passed=False,
            severity=AssetCheckSeverity.WARN,
            description=(
                f"Diferença de {diff_pct:.1f}% entre Bronze ({bronze}) "
                f"e Silver ({silver}) — tolerância: {TOLERANCIA_PCT}%"
            ),
            metadata={
                "bronze_count": bronze,
                "silver_count": silver,
                "diff_pct": round(diff_pct, 1),
            },
        )

    logger.info("CHECK OK: previsoes Bronze=%s Silver=%s (dif=%.1f%%)", bronze, silver, diff_pct)
    return AssetCheckResult(
        passed=True,
        description=(
            f"Bronze ({bronze}) ↔ Silver ({silver}) — diferença de {diff_pct:.1f}% (tolerância: {TOLERANCIA_PCT}%)"
        ),
        metadata={
            "bronze_count": bronze,
            "silver_count": silver,
            "diff_pct": round(diff_pct, 1),
        },
    )
