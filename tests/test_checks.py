"""Testes dos AssetChecks de qualidade entre camadas."""

import os
import tempfile


class TestChecksBronzeSilver:
    def test_posicoes_check_passes(self, monkeypatch):
        """Check passa quando não há dados em nenhuma camada."""
        import src.compactar_parquet
        from assets.checks import check_posicoes_bronze_silver

        # Aponta para diretórios vazios (sem DB e sem Parquet)
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(src.compactar_parquet, "DB_PATH", os.path.join(tmp, "nonexistent.db"))
            monkeypatch.setattr(src.compactar_parquet, "PARQUET_DIR", os.path.join(tmp, "parquet"))

            result = check_posicoes_bronze_silver()
            assert result.passed is True

    def test_previsoes_check_passes(self, monkeypatch):
        """Check de previsões passa quando não há dados em nenhuma camada."""
        import src.compactar_parquet
        from assets.checks import check_previsoes_bronze_silver

        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(src.compactar_parquet, "DB_PATH", os.path.join(tmp, "nonexistent.db"))
            monkeypatch.setattr(src.compactar_parquet, "PARQUET_DIR", os.path.join(tmp, "parquet"))

            result = check_previsoes_bronze_silver()
            assert result.passed is True

    def test_posicoes_check_with_data(self, monkeypatch):
        """Check com dados sintéticos — contagens iguais."""
        import src.compactar_parquet
        from assets.checks import check_posicoes_bronze_silver

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "test.db")
            pq_dir = os.path.join(tmp, "parquet")
            pq_table = os.path.join(pq_dir, "posicoes")
            monkeypatch.setattr(src.compactar_parquet, "DB_PATH", db_path)
            monkeypatch.setattr(src.compactar_parquet, "PARQUET_DIR", pq_dir)

            import sqlite3

            import duckdb

            # Cria SQLite com dados
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE posicoes (id INTEGER PRIMARY KEY, timestamp_coleta DATETIME, "
                "id_onibus INTEGER, latitude REAL, longitude REAL)"
            )
            conn.execute("INSERT INTO posicoes VALUES (1, '2025-08-13 10:00', 123, -23.5, -46.6)")
            conn.execute("INSERT INTO posicoes VALUES (2, '2025-08-13 10:05', 456, -23.6, -46.7)")
            conn.commit()
            conn.close()

            # Cria Parquet equivalente (usa f-string pois DuckDB não aceita ? em COPY TO path)
            os.makedirs(pq_table, exist_ok=True)
            con = duckdb.connect()
            con.execute(
                f"COPY (SELECT *, CAST(timestamp_coleta AS DATE) AS dt "
                f"FROM sqlite_scan('{db_path}', 'posicoes')) "
                f"TO '{pq_table}' (FORMAT PARQUET, PARTITION_BY (dt))"
            )
            con.close()

            result = check_posicoes_bronze_silver()
            assert result.passed is True

    def test_asset_checks_registered(self):
        """Verifica que os asset_checks estão registrados nas Definitions."""
        from assets import defs

        checks = list(defs.asset_checks)
        assert len(checks) >= 1
        # AssetChecksDefinition tem check_specs (lista de AssetCheckSpec)
        check_names = set()
        for c in checks:
            for spec in c.check_specs:
                check_names.add(spec.name)
        assert "check_posicoes_bronze_silver" in check_names
        assert "check_previsoes_bronze_silver" in check_names
