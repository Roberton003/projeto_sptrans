"""Testes da tabela de linhagem e metadata nos assets."""

import os
import tempfile


class TestRegistrarLinhagem:
    def test_registrar_e_consultar(self):
        """Insere e consulta registro na tabela lineage_audit."""
        from src.database import registrar_linhagem, schema_sql

        # Usa SQLite temporário
        with tempfile.TemporaryDirectory() as tmp:
            # Forçamos caminho temporário via patch
            import sqlite3

            db_path = os.path.join(tmp, "test_linhagem.db")
            conn = sqlite3.connect(db_path)
            tables, indexes = schema_sql()
            for t in tables:
                conn.execute(t)
            for idx in indexes:
                conn.execute(idx)
            conn.commit()
            conn.close()

            # Patch DB_PATH
            import src.database

            original_db = src.database.DB_PATH
            original_sqlite = src.database.SQLITE_PATH
            src.database.DB_PATH = db_path
            src.database.SQLITE_PATH = db_path

            try:
                registrar_linhagem("test_asset", "posicoes", "bronze", 100, "ok")
                conn2 = sqlite3.connect(db_path)
                row = conn2.execute(
                    "SELECT asset_name, table_name, layer, row_count, status FROM lineage_audit"
                ).fetchone()
                conn2.close()
                assert row is not None
                assert row[0] == "test_asset"
                assert row[1] == "posicoes"
                assert row[2] == "bronze"
                assert row[3] == 100
                assert row[4] == "ok"
            finally:
                src.database.DB_PATH = original_db
                src.database.SQLITE_PATH = original_sqlite

    def test_registrar_sem_banco(self):
        """Não deve levantar exceção se o banco não existir."""
        from src.database import registrar_linhagem

        # Deve apenas logar warning, não levantar
        registrar_linhagem("test", "tabela", "bronze", 0, "ok")


class TestAssetsMetadata:
    def test_assets_posicoes_metadata(self):
        """Asset posicoes_sptrans retorna Output com metadata."""
        # Mock para evitar chamada real à API
        import src.coleta_sptrans
        from assets.coleta import posicoes_sptrans

        original_job = src.coleta_sptrans.job
        src.coleta_sptrans.job = lambda letreiros: None

        original_get_config = src.coleta_sptrans.get_config
        src.coleta_sptrans.get_config = lambda: {}
        src.coleta_sptrans.get_linhas_alvo_ids = lambda c: []
        src.coleta_sptrans.get_letreiros_alvo = lambda ids: []

        try:
            result = posicoes_sptrans()
            assert hasattr(result, "metadata")
            meta = result.metadata
            # MetadataValue wrappers — acessar .text para o valor string
            assert meta["layer"].text == "bronze"
            assert meta["table"].text == "posicoes"
            assert "row_count" in meta
        finally:
            src.coleta_sptrans.job = original_job
            src.coleta_sptrans.get_config = original_get_config

    def test_assets_previsoes_metadata(self):
        """Asset previsoes_sptrans retorna Output com metadata."""

        import src.coleta_previsoes
        from assets.coleta import previsoes_sptrans

        original_job = src.coleta_previsoes.job
        original_autenticar = src.coleta_previsoes.autenticar
        src.coleta_previsoes.job = lambda session, linhas: None
        src.coleta_previsoes.autenticar = lambda token, session: True

        original_get_config = src.coleta_previsoes.get_config
        original_get_token = src.coleta_previsoes.get_token
        original_get_linhas = src.coleta_previsoes.get_linhas_alvo
        src.coleta_previsoes.get_config = lambda: {}
        src.coleta_previsoes.get_token = lambda c: "fake"
        src.coleta_previsoes.get_linhas_alvo = lambda c: []

        try:
            result = previsoes_sptrans()
            assert hasattr(result, "metadata")
            meta = result.metadata
            # MetadataValue wrappers — acessar .text para o valor string
            assert meta["layer"].text == "bronze"
            assert meta["table"].text == "previsoes"
        finally:
            src.coleta_previsoes.job = original_job
            src.coleta_previsoes.autenticar = original_autenticar
            src.coleta_previsoes.get_config = original_get_config
            src.coleta_previsoes.get_token = original_get_token
            src.coleta_previsoes.get_linhas_alvo = original_get_linhas
