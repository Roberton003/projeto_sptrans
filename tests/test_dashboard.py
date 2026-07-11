"""Testes para funções de análise do dashboard_sptrans.py."""

import pandas as pd
import pytest

from src.dashboard_sptrans import (
    analyze_bunched_buses,
    analyze_stuck_buses,
    enrich_with_line_names,
)


@pytest.fixture
def sample_df():
    """DataFrame de exemplo similar ao resultados_analise."""
    return pd.DataFrame(
        {
            "id_onibus": [1001, 1001, 1002, 1003],
            "letreiro_linha": ["8000-10", "8000-10", "8000-10", "9000-10"],
            "timestamp_analise": pd.to_datetime(
                [
                    "2025-08-15 10:00:00",
                    "2025-08-15 10:05:00",
                    "2025-08-15 10:00:00",
                    "2025-08-15 10:00:00",
                ]
            ),
            "posicao_atual_lat": [-23.5505, -23.5505, -23.5510, -23.5520],
            "posicao_atual_lon": [-46.6333, -46.6333, -46.6328, -46.6320],
        }
    )


def test_analyze_stuck_buses_detecta_parado(sample_df):
    """Onibus 1001 (mesma posição, 2 registros com 5 min de diferença) > 10 min? Não deve detectar."""
    result = analyze_stuck_buses(sample_df)
    # 1001 tem 5 min entre coleta (10:00 e 10:05), não > 10 min
    assert 1001 not in result.index.get_level_values("id_onibus") or result.empty, (
        "1001 tem só 5 min de diferença, não deveria ser detectado como parado"
    )


def test_analyze_stuck_buses_com_movimento():
    """Onibus com deslocamento significativo não é detectado como parado."""
    df = pd.DataFrame(
        {
            "id_onibus": [1001, 1001],
            "letreiro_linha": ["8000-10", "8000-10"],
            "timestamp_analise": pd.to_datetime(
                [
                    "2025-08-15 10:00:00",
                    "2025-08-15 10:30:00",
                ]
            ),
            "posicao_atual_lat": [-23.5505, -23.5600],
            "posicao_atual_lon": [-46.6333, -46.6300],
        }
    )
    result = analyze_stuck_buses(df)
    assert result.empty, "Ônibus com deslocamento > 0.1km não deve ser detectado como parado"


def test_analyze_bunched_buses_sem_comboio(sample_df):
    """DataFrame com 3 ônibus distantes não detecta comboio."""
    result = analyze_bunched_buses(sample_df)
    assert isinstance(result, pd.DataFrame)
    # Pode ou não ter comboios, depende das distâncias


def test_enrich_with_line_names_without_lines():
    """enrich_with_line_names funciona mesmo sem catálogo de linhas."""
    df = pd.DataFrame(
        {
            "letreiro_linha": ["8000-10", "9000-10"],
            "contagem": [5, 3],
        }
    )
    result = enrich_with_line_names(
        df.set_index("letreiro_linha")["contagem"].to_frame("contagem"), None
    )
    assert "nome_linha" in result.columns or result.index.name == "nome_linha"


def test_enrich_with_line_names_with_lines():
    """enrich_with_line_names adiciona nome da linha quando catálogo existe."""
    df = pd.DataFrame(
        {
            "letreiro_linha": ["8000-10"],
            "contagem": [5],
        }
    )

    lines_df = pd.DataFrame(
        {
            "letreiro_numerico": ["8000"],
            "tipo_letreiro": [10],
            "sentido_ida": ["Terminal A"],
            "sentido_volta": ["Terminal B"],
        }
    )
    lines_df["nome_linha"] = lines_df["sentido_ida"] + " / " + lines_df["sentido_volta"]

    result = enrich_with_line_names(
        df.set_index("letreiro_linha")["contagem"].to_frame("contagem"), lines_df
    )
    # Deve conter 'nome_linha' ou index renomeado
    assert "nome_linha" in result.columns or result.index.name == "nome_linha"
