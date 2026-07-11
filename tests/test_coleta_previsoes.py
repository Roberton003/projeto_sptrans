"""Testes para coleta_previsoes.py — autenticação, coleta e DB."""

import json
from unittest.mock import MagicMock, patch

from src.coleta_previsoes import (
    autenticar,
    coletar_previsao_linha,
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


def test_autenticar_falha():
    """Autenticação retorna False quando API responde False."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = False
    mock_session.post.return_value = mock_resp

    result = autenticar("fake_token", mock_session)
    assert result is False


def test_coletar_previsao_sucesso():
    """Coleta de previsão retorna JSON quando API responde."""
    resposta = {
        "ps": [
            {
                "cp": 5001,
                "vs": [{"p": 1001, "t": "2025-08-15T10:15:00"}],
            }
        ]
    }
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = resposta
    mock_session.get.return_value = mock_resp

    result = coletar_previsao_linha(mock_session, 2411)
    assert result == resposta


def test_coletar_previsao_erro_rede():
    """Coleta de previsão retorna None em erro de rede."""
    import requests

    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectionError("timeout")

    result = coletar_previsao_linha(mock_session, 2411)
    assert result is None


def test_coletar_previsao_json_invalido():
    """Coleta de previsão retorna None em JSON inválido."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
    mock_session.get.return_value = mock_resp

    result = coletar_previsao_linha(mock_session, 2411)
    assert result is None


@patch("src.coleta_previsoes.coletar_previsao_linha")
def test_job_sem_linhas(mock_coletar):
    """Job com lista de linhas vazia não faz coleta."""
    mock_session = MagicMock()
    result = job(mock_session, [])
    assert result is None
    mock_coletar.assert_not_called()


@patch("src.coleta_previsoes.coletar_previsao_linha")
def test_job_linhas_sem_dados(mock_coletar):
    """Job com linha que não retorna dados não quebra."""
    mock_coletar.return_value = None
    mock_session = MagicMock()
    result = job(mock_session, [2411])
    assert result is None


@patch("src.coleta_previsoes.coletar_previsao_linha")
def test_job_com_dados_processa_registros(mock_coletar):
    """Job processa dados de previsão corretamente."""
    mock_coletar.return_value = {
        "ps": [
            {
                "cp": 5001,
                "vs": [
                    {"p": 1001, "t": "2025-08-15T10:15:00"},
                    {"p": 1002, "t": "2025-08-15T10:12:00"},
                ],
            }
        ]
    }
    mock_session = MagicMock()

    from contextlib import contextmanager

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    @contextmanager
    def mock_get_connection():
        yield mock_conn

    with patch("src.coleta_previsoes.get_connection", mock_get_connection):
        job(mock_session, [2411])

    # Verifica que executemany foi chamado com 2 registros
    # (commit é feito automaticamente pelo context manager de get_connection)
    args, _ = mock_cursor.executemany.call_args
    registros = args[1]
    assert len(registros) == 2
    assert registros[0][1] == 2411  # id_linha
    assert registros[1][1] == 2411
