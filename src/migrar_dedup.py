"""
Script de migração one-shot (2026-07-11).

Remove duplicatas das tabelas `posicoes` e `previsoes` e cria os índices UNIQUE
que garantem idempotência dos coletores (INSERT OR IGNORE).

Pode ser executado múltiplas vezes sem efeito colateral (idempotente).

Uso:
    python src/migrar_dedup.py
"""

import logging
import os
import sqlite3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DB_PATH = os.path.join("data", "sptrans_data.db")


def remover_duplicatas(cursor, tabela, chaves, nome_idx):
    """Remove duplicatas mantendo a linha com menor `id` e cria UNIQUE INDEX."""
    placeholders = ", ".join(chaves)
    logging.info(f"Tabela '{tabela}': identificando duplicatas por ({placeholders})...")

    # Deleta duplicatas (mantém menor id)
    cursor.execute(f"""
        DELETE FROM {tabela}
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM {tabela}
            GROUP BY {placeholders}
        )
    """)
    removidos = cursor.rowcount
    if removidos:
        logging.info(f"  → {removidos} registro(s) duplicado(s) removido(s).")
    else:
        logging.info("  → Nenhuma duplicata encontrada.")

    # Cria UNIQUE INDEX (se não existir)
    cols_sql = ", ".join(chaves)
    cursor.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {nome_idx}
        ON {tabela}({cols_sql})
    """)
    logging.info(f"  → Índice '{nome_idx}' verificado/criado.")


def main():
    if not os.path.exists(DB_PATH):
        logging.warning(f"Banco {DB_PATH} não encontrado. Nada a migrar.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    remover_duplicatas(
        cursor,
        "posicoes",
        ["timestamp_coleta", "id_onibus"],
        "idx_posicoes_dedup",
    )

    remover_duplicatas(
        cursor,
        "previsoes",
        ["timestamp_coleta", "id_linha", "id_onibus", "id_parada", "horario_previsao"],
        "idx_previsoes_dedup",
    )

    conn.commit()
    conn.close()
    logging.info("Migração de deduplicação concluída com sucesso.")


if __name__ == "__main__":
    main()
