"""
Análise de frota SPTrans: cruza posições com previsões e salva resultados.

Modo analítico (Parquet via DuckDB):
    python src/analise_onibus.py --mode parquet

Modo legado (SQLite direto):
    python src/analise_onibus.py --mode sqlite  (ou omite --mode)

No modo parquet, os dados históricos são lidos de data/parquet/ via DuckDB,
com fallback para SQLite se o Parquet não existir.
"""

import argparse
import logging
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_PATH = os.path.join("data", "sptrans_data.db")
PARQUET_DIR = os.path.join("data", "parquet")


def _load_via_sqlite():
    """Carrega dados via SQLite direto (modo legado)."""
    import sqlite3

    import pandas as pd

    if not os.path.exists(DB_PATH):
        logging.error(f"Banco não encontrado em {DB_PATH}.")
        return None, None

    conn = sqlite3.connect(DB_PATH)
    posicoes_df = pd.read_sql_query("SELECT * FROM posicoes", conn)
    previsoes_df = pd.read_sql_query("SELECT * FROM previsoes", conn)
    conn.close()
    logging.info(f"SQLite: {len(posicoes_df)} posições, {len(previsoes_df)} previsões.")
    return posicoes_df, previsoes_df


def _load_via_parquet():
    """Carrega dados via DuckDB sobre os Parquet (modo analítico)."""
    import duckdb
    import pandas as pd

    pos_path = os.path.join(PARQUET_DIR, "posicoes")
    prev_path = os.path.join(PARQUET_DIR, "previsoes")

    if not os.path.isdir(pos_path):
        logging.warning(
            f"Parquet não encontrado em {pos_path}. Usando fallback SQLite."
        )
        return _load_via_sqlite()

    con = duckdb.connect()
    posicoes_df = con.execute(
        f"SELECT * EXCLUDE (dt) FROM read_parquet('{pos_path}/**/*.parquet')"
    ).fetchdf()
    if os.path.isdir(prev_path):
        previsoes_df = con.execute(
            f"SELECT * EXCLUDE (dt) FROM read_parquet('{prev_path}/**/*.parquet')"
        ).fetchdf()
    else:
        previsoes_df = pd.DataFrame()
    con.close()
    logging.info(
        f"Parquet: {len(posicoes_df)} posições, {len(previsoes_df)} previsões."
    )
    return posicoes_df, previsoes_df


def main():
    parser = argparse.ArgumentParser(
        description="Análise de frota SPTrans (Parquet ou SQLite)"
    )
    parser.add_argument(
        "--mode",
        choices=["sqlite", "parquet"],
        default="sqlite",
        help="Fonte de dados: sqlite (legado, padrão) ou parquet (DuckDB)",
    )
    args = parser.parse_args()

    from datetime import datetime

    import pandas as pd

    if args.mode == "parquet":
        posicoes_df, previsoes_df = _load_via_parquet()
    else:
        posicoes_df, previsoes_df = _load_via_sqlite()

    if posicoes_df is None or posicoes_df.empty:
        logging.warning("Nenhum dado de posição. Encerrando.")
        return

    # --- Processamento (idêntico ao original) ---
    if previsoes_df is not None and not previsoes_df.empty:
        previsoes_df_unicas = previsoes_df.sort_values(
            by="horario_previsao"
        ).drop_duplicates(subset=["id_onibus"], keep="first")
        logging.info(f"{len(previsoes_df_unicas)} previsões únicas (uma por ônibus).")
        df_final = pd.merge(
            posicoes_df, previsoes_df_unicas, on="id_onibus", how="left"
        )
    else:
        df_final = posicoes_df

    df_final["timestamp_analise"] = datetime.now()
    df_final.rename(
        columns={
            "latitude": "posicao_atual_lat",
            "longitude": "posicao_atual_lon",
            "timestamp_posicao": "horario_posicao",
            "id_parada": "proximo_ponto_previsto",
            "horario_previsao": "horario_previsto_chegada",
        },
        inplace=True,
    )

    colunas_tabela = [
        "timestamp_analise",
        "id_onibus",
        "letreiro_linha",
        "posicao_atual_lat",
        "posicao_atual_lon",
        "horario_posicao",
        "proximo_ponto_previsto",
        "horario_previsto_chegada",
    ]
    for col in colunas_tabela:
        if col not in df_final.columns:
            df_final[col] = None
    df_final = df_final[colunas_tabela]

    # Salva resultados no SQLite (sempre, independente da fonte)
    import sqlite3

        # Renomear para schema do resultados_analise
        df_final = df_final.rename(columns={
            "latitude": "posicao_atual_lat",
            "longitude": "posicao_atual_lon",
            "timestamp_posicao": "horario_posicao",
            "id_parada": "proximo_ponto_previsto",
            "horario_previsao": "horario_previsto_chegada",
        })
        df_final["timestamp_analise"] = datetime.now()

    # Salva resultados no SQLite (sempre, independente da fonte)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resultados_analise;")
    conn.commit()
    df_final.to_sql("resultados_analise", conn, if_exists="append", index=False)
    conn.close()
    logging.info(
        f"Análise concluída: {len(df_final)} resultados salvos em resultados_analise."
    )

if __name__ == "__main__":
    main()
