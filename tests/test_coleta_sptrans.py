"""Testes para coleta_sptrans.py — autenticação, coleta, filtro e DB."""

import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

from src.coleta_sptrans import (
    autenticar,
    coletar_posicoes,
    job,
)


def test_autenticar_sucesso():
    """Autenticação retorna True quando API responde True."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = True
    mock_session.post.return_value = mock_resp

    result = autenticar("fake_token", mock_session)
    assert result is True
    mock_session.post.assert_called_once()


def test_autenticar_falha():
    """Autenticação retorna False quando API responde False."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = False
    mock_session.post.return_value = mock_resp

    result = autenticar("fake_token", mock_session)
    assert result is False


def test_autenticar_exception():
    """Autenticação retorna False em erro de rede."""
    import requests

    mock_session = MagicMock()
    mock_session.post.side_effect = requests.exceptions.ConnectionError("timeout")

    result = autenticar("fake_token", mock_session)
    assert result is False


def test_coletar_posicoes_sucesso():
    """Coleta retorna JSON quando API responde com dados válidos."""
    resposta_api = {
        "l": [
            {
                "c": "8000-10",
                "vs": [{"p": 1001, "py": -23.55, "px": -46.63, "ta": "2025-08-15 10:00:00"}],
            }
        ]
    }
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = resposta_api
    mock_session.get.return_value = mock_resp

    result = coletar_posicoes(mock_session)
    assert result == resposta_api


def test_coletar_posicoes_erro_rede():
    """Coleta retorna None em erro de rede."""
    import requests

    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectionError("timeout")

    result = coletar_posicoes(mock_session)
    assert result is None


def test_coletar_posicoes_json_invalido():
    """Coleta retorna None quando resposta não é JSON válido."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
    mock_session.get.return_value = mock_resp

    result = coletar_posicoes(mock_session)
    assert result is None


@patch("src.coleta_sptrans.get_config")
@patch("src.coleta_sptrans.get_token")
@patch("src.coleta_sptrans.autenticar")
@patch("src.coleta_sptrans.coletar_posicoes")
def test_job_config_erro_aborta(mock_coletar, mock_autenticar, mock_get_token, mock_get_config):
    """Job aborta quando get_config levanta exceção."""
    mock_get_config.side_effect = FileNotFoundError("config não encontrado")

    with patch("src.coleta_sptrans.datetime") as mock_dt:
        mock_dt.now.return_value.time.return_value = _make_time(10, 0)

        # Sem letreiros_alvo (vazio), job deve tentar config e falhar
        # Precisamos de um letreiro para passar pelo bloco de criação do letreiro
        # Na verdade, job(set()) primeiro verifica horário, depois chama get_config
        # que vai falhar
        result = job(set())
        assert result is None
        mock_coletar.assert_not_called()


def _make_time(hour, minute):
    """Helper: cria objeto time para mock."""

    class FakeTime:
        def __init__(self, h, m):
            self.hour = h
            self.minute = m

        def __ge__(self, other):
            if hasattr(other, "hour"):
                return (self.hour, self.minute) >= (other.hour, getattr(other, "minute", 0))
            return NotImplemented

        def __le__(self, other):
            if hasattr(other, "hour"):
                return (self.hour, self.minute) <= (other.hour, getattr(other, "minute", 0))
            return NotImplemented

        def __repr__(self):
            return f"{self.hour:02d}:{self.minute:02d}"

    return FakeTime(hour, minute)


@patch("src.coleta_sptrans.get_config")
@patch("src.coleta_sptrans.get_token")
@patch("src.coleta_sptrans.autenticar")
@patch("src.coleta_sptrans.coletar_posicoes")
def test_job_com_dados_salva_no_db(mock_coletar, mock_autenticar, mock_get_token, mock_get_config):
    """Job com dados válidos insere registros filtrados no SQLite."""
    mock_get_config.return_value = {
        "SPTRANS": {"TOKEN": "x"},
        "COLETA": {"LINHAS_ALVO": "2411"},
    }
    mock_get_token.return_value = "x"
    mock_autenticar.return_value = True
    mock_coletar.return_value = {
        "l": [
            {
                "c": "8000-10",
                "vs": [
                    {"p": 1001, "py": -23.55, "px": -46.63, "ta": "2025-08-15 10:00:00"},
                    {"p": 1002, "py": -23.56, "px": -46.64, "ta": "2025-08-15 10:01:00"},
                ],
            },
            {
                "c": "9000-10",
                "vs": [
                    {"p": 3001, "py": -23.57, "px": -46.65, "ta": "2025-08-15 10:02:00"},
                ],
            },
        ]
    }

    import datetime as dt

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS posicoes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp_coleta DATETIME NOT NULL, "
            "id_onibus INTEGER NOT NULL, "
            "letreiro_linha TEXT, "
            "latitude REAL NOT NULL, "
            "longitude REAL NOT NULL, "
            "timestamp_posicao DATETIME"
            ")"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_posicoes_dedup "
            "ON posicoes(timestamp_coleta, id_onibus)"
        )
        conn.commit()
        conn.close()

        real_now = dt.datetime(2025, 8, 15, 10, 0, 0)

        with patch("src.coleta_sptrans.DB_PATH", db_path):
            with patch("src.coleta_sptrans.datetime") as mock_dt:
                mock_dt.now.return_value = real_now

                job({"8000-10"})

        # Verifica que apenas 8000-10 foi inserido (não 9000-10)
        conn2 = sqlite3.connect(db_path)
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT id_onibus, letreiro_linha FROM posicoes")
        rows = cursor2.fetchall()
        conn2.close()

        assert len(rows) == 2, "Deveria inserir 2 registros (apenas 8000-10)"
        assert all(r[1] == "8000-10" for r in rows), "Apenas letreiro 8000-10"

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
