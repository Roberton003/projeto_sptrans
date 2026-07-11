"""Testes dos contratos de dados (Pydantic models) para cada camada."""

from datetime import datetime

import pytest
from pydantic import ValidationError


class TestPosicaoBronze:
    def test_valido(self):
        from src.contracts import PosicaoBronze

        rec = PosicaoBronze(
            timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
            id_onibus=12345,
            letreiro_linha="978M-10",
            latitude=-23.55,
            longitude=-46.63,
            timestamp_posicao=datetime(2025, 8, 13, 10, 0, 5),
        )
        assert rec.id_onibus == 12345
        assert rec.letreiro_linha == "978M-10"

    def test_campos_obrigatorios(self):
        from src.contracts import PosicaoBronze

        with pytest.raises(ValidationError):
            PosicaoBronze(
                timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
                id_onibus=-1,  # inválido: gt=0
                latitude=-23.55,
                longitude=-46.63,
            )

    def test_latitude_invalida(self):
        from src.contracts import PosicaoBronze

        with pytest.raises(ValidationError):
            PosicaoBronze(
                timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
                id_onibus=12345,
                latitude=100.0,  # > 90
                longitude=-46.63,
            )

    def test_extra_ignored(self):
        from src.contracts import PosicaoBronze

        rec = PosicaoBronze(
            timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
            id_onibus=12345,
            latitude=-23.55,
            longitude=-46.63,
            campo_extra="ignorado",
        )
        assert not hasattr(rec, "campo_extra")


class TestPrevisaoBronze:
    def test_valido(self):
        from src.contracts import PrevisaoBronze

        rec = PrevisaoBronze(
            timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
            id_linha=123,
            id_onibus=45678,
            id_parada=9012,
            horario_previsao="2025-08-13T10:15:00",
        )
        assert rec.id_linha == 123
        assert rec.horario_previsao == "2025-08-13T10:15:00"

    def test_id_onibus_invalido(self):
        from src.contracts import PrevisaoBronze

        with pytest.raises(ValidationError):
            PrevisaoBronze(
                timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
                id_linha=123,
                id_onibus=0,  # inválido: gt=0
            )


class TestPosicaoSilver:
    def test_valido(self):
        from src.contracts import PosicaoSilver

        rec = PosicaoSilver(
            timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
            id_onibus=12345,
            latitude=-23.55,
            longitude=-46.63,
            dt="2025-08-13",
        )
        assert rec.dt == "2025-08-13"

    def test_dt_invalido(self):
        from src.contracts import PosicaoSilver

        with pytest.raises(ValidationError):
            PosicaoSilver(
                timestamp_coleta=datetime(2025, 8, 13, 10, 0, 0),
                id_onibus=12345,
                latitude=-23.55,
                longitude=-46.63,
                dt="13-08-2025",  # formato errado
            )


class TestValidarLote:
    def test_lote_sem_erros(self):
        from src.contracts import PosicaoBronze, validar_lote

        registros = [
            {
                "timestamp_coleta": datetime(2025, 8, 13, 10, 0, 0),
                "id_onibus": 123,
                "latitude": -23.55,
                "longitude": -46.63,
            },
            {
                "timestamp_coleta": datetime(2025, 8, 13, 10, 0, 0),
                "id_onibus": 456,
                "latitude": -23.56,
                "longitude": -46.64,
            },
        ]
        erros = validar_lote(PosicaoBronze, registros)
        assert erros == []

    def test_lote_com_erros(self):
        from src.contracts import PosicaoBronze, validar_lote

        registros = [
            {
                "timestamp_coleta": datetime(2025, 8, 13, 10, 0, 0),
                "id_onibus": 123,
                "latitude": -23.55,
                "longitude": -46.63,
            },
            {
                "timestamp_coleta": datetime(2025, 8, 13, 10, 0, 0),
                "id_onibus": 0,  # inválido
                "latitude": -23.56,
                "longitude": -46.64,
            },
        ]
        erros = validar_lote(PosicaoBronze, registros)
        assert len(erros) == 1
        assert erros[0]["indice"] == 1
