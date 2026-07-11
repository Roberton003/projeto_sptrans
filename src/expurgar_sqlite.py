"""
Expurgo da janela quente SQLite.

Remove registros com mais de N dias de `data/sptrans_data.db`, mantendo apenas
a janela operacional definida (padrão: 7 dias).

O histórico completo permanece em Parquet (data/parquet/).

Uso:
    python src/expurgar_sqlite.py                       # remove > 7 dias
    python src/expurgar_sqlite.py --dias 14              # remove > 14 dias
    python src/expurgar_sqlite.py --dry-run              # só mostra o que seria removido
"""

import argparse
import logging
import os
from datetime import datetime, timedelta

from src.database import DB_PATH, get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def expurgar(conn, tabela, limite, dry_run=False):
    """Remove registros da tabela com timestamp_coleta anterior ao limite."""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT count(*) FROM {tabela} WHERE timestamp_coleta < ?",
        (limite.isoformat(),),
    )
    total = cursor.fetchone()[0]

    if total == 0:
        logging.info(f"  '{tabela}': nenhum registro para expurgar.")
        return 0

    if dry_run:
        logging.info(f"  '{tabela}': {total} registros seriam removidos (dry-run).")
        return total

    cursor.execute(
        f"DELETE FROM {tabela} WHERE timestamp_coleta < ?",
        (limite.isoformat(),),
    )
    conn.commit()
    removidos = cursor.rowcount
    logging.info(f"  '{tabela}': {removidos} registros expurgados.")
    return removidos


def main():
    parser = argparse.ArgumentParser(description="Expurga janela quente do SQLite (mantém apenas N dias recentes)")
    parser.add_argument(
        "--dias",
        type=int,
        default=7,
        help="Número de dias a manter (padrão: 7). Registros mais antigos são removidos.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas exibe o que seria removido, sem modificar o banco.",
    )
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        logging.warning(f"Banco {DB_PATH} não encontrado. Nada a fazer.")
        return

    limite = datetime.now() - timedelta(days=args.dias)
    logging.info(
        f"Expurgando registros anteriores a {limite.date()} ({'dry-run' if args.dry_run else 'executando'})..."
    )

    with get_connection() as conn:
        total = 0
        for tabela in ("posicoes", "previsoes"):
            total += expurgar(conn, tabela, limite, dry_run=args.dry_run)

    if not args.dry_run:
        logging.info(f"Total expurgado: {total} registros.")
    else:
        logging.info(f"Dry-run concluído. {total} registros seriam removidos.")


if __name__ == "__main__":
    main()
