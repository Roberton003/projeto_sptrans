"""
Compactação SQLite → Parquet particionado (idempotente).

Exporta dados do SQLite para Parquet particionado por data (dt=YYYY-MM-DD),
usando DuckDB. Idempotente por partição: executar 2× sobre o mesmo dia
produz Parquet idêntico (OVERWRITE_OR_IGNORE).

Uso:
    python src/compactar_parquet.py              # exporta tudo
    python src/compactar_parquet.py --date YYYY-MM-DD  # dia específico

Dependências: duckdb, pyarrow (pip install duckdb pyarrow)
"""

import argparse
import logging
import os

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DB_PATH = os.path.join("data", "sptrans_data.db")
PARQUET_DIR = os.path.join("data", "parquet")


def exportar_tabela(con, tabela, filtro_data=None):
    """Exporta tabela do SQLite para Parquet particionado por dt."""
    destino = os.path.join(PARQUET_DIR, tabela)
    os.makedirs(destino, exist_ok=True)

    # Cria tabela temporária no DuckDB com a partição dt
    if filtro_data:
        logging.info(f"Exportando '{tabela}' (dt={filtro_data}) → {destino} ...")
        con.execute(f"""
            CREATE OR REPLACE TABLE __temp_export AS
            SELECT *, CAST(timestamp_coleta AS DATE) AS dt
            FROM sqlite_scan('{DB_PATH}', '{tabela}')
            WHERE CAST(timestamp_coleta AS DATE) = '{filtro_data}'
        """)
    else:
        logging.info(f"Exportando '{tabela}' (completo) → {destino} ...")
        con.execute(f"""
            CREATE OR REPLACE TABLE __temp_export AS
            SELECT *, CAST(timestamp_coleta AS DATE) AS dt
            FROM sqlite_scan('{DB_PATH}', '{tabela}')
        """)

    rows = con.execute("SELECT count(*) FROM __temp_export").fetchone()[0]
    if rows == 0:
        logging.info("  → Nenhum registro para exportar. Pulando.")
        return 0

    con.execute(f"""
        COPY __temp_export TO '{destino}'
        (FORMAT PARQUET, PARTITION_BY (dt), OVERWRITE_OR_IGNORE)
    """)

    con.execute("DROP TABLE IF EXISTS __temp_export")

    # Verificação pós-escrita
    count = con.execute(
        f"SELECT count(*) FROM read_parquet('{destino}/**/*.parquet')"
    ).fetchone()[0]
    logging.info(f"  → {count} registros exportados para Parquet.")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Compacta SQLite → Parquet particionado (idempotente)"
    )
    parser.add_argument(
        "--date",
        help="Exportar apenas uma data específica (YYYY-MM-DD). Omite para exportar tudo.",
    )
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        logging.error(f"Banco não encontrado: {DB_PATH}")
        return

    con = duckdb.connect()
    os.makedirs(PARQUET_DIR, exist_ok=True)

    exportar_tabela(con, "posicoes", filtro_data=args.date)
    exportar_tabela(con, "previsoes", filtro_data=args.date)

    con.close()
    logging.info("Compactação concluída com sucesso.")


if __name__ == "__main__":
    main()
