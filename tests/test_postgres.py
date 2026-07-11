"""Testes de integração com PostgreSQL.

Requer DATABASE_URL configurada e PostgreSQL rodando.
Ignorado automaticamente se as condições não forem satisfeitas.
"""

import pytest

from src.database import DATABASE_URL, IS_POSTGRES

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL não configurada — ignorando testes PostgreSQL",
)


def test_database_url_configurada():
    """DATABASE_URL está configurada e IS_POSTGRES reflete corretamente."""
    assert DATABASE_URL is not None
    assert IS_POSTGRES is True


def test_get_connection_postgres():
    """get_connection() retorna conexão PostgreSQL funcional."""
    from src.database import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1


def test_schema_creation_postgres():
    """Schema SQL PostgreSQL é executado sem erros."""
    from src.database import get_connection, schema_sql

    tables, indexes = schema_sql()
    with get_connection() as conn:
        cursor = conn.cursor()
        for sql in tables:
            cursor.execute(sql)
        for sql in indexes:
            cursor.execute(sql)

    # Verifica que as tabelas existem
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables_found = {row[0] for row in cursor.fetchall()}
        assert "posicoes" in tables_found
        assert "previsoes" in tables_found
        assert "resultados_analise" in tables_found


def test_insert_on_conflict_do_nothing():
    """INSERT duplicado no PostgreSQL não gera erro (ON CONFLICT DO NOTHING)."""
    from src.database import get_connection, insert_sql

    sql = insert_sql(
        "posicoes",
        ["timestamp_coleta", "id_onibus", "letreiro_linha", "latitude", "longitude"],
    )

    with get_connection() as conn:
        cursor = conn.cursor()
        # Primeira inserção
        cursor.execute(
            sql,
            ("2025-08-15 10:00:00", 1001, "8000-10", -23.55, -46.63),
        )
        # Segunda inserção (mesma chave) — deve ser ignorada sem erro
        cursor.execute(
            sql,
            ("2025-08-15 10:00:00", 1001, "8000-10", -23.55, -46.63),
        )

        cursor.execute("SELECT count(*) FROM posicoes")
        count = cursor.fetchone()[0]
        assert count >= 1, "ON CONFLICT DO NOTHING deveria ignorar duplicata"


def test_migrar_script():
    """Script de migração pode ser importado sem erros."""
    from src import migrar_postgres

    assert hasattr(migrar_postgres, "migrar")
    assert hasattr(migrar_postgres, "TABELAS")
