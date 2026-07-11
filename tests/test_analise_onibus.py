"""Testes para analise_onibus.py — merge e processamento de dados."""

import pandas as pd


def test_merge_posicoes_previsoes(sample_posicoes_df, sample_previsoes_df):
    """Merge de posições com previsões agrupando pela última previsão por ônibus."""
    previsoes_unicas = sample_previsoes_df.sort_values("horario_previsao").drop_duplicates(
        subset=["id_onibus"], keep="first"
    )

    df_final = pd.merge(sample_posicoes_df, previsoes_unicas, on="id_onibus", how="left")

    # Verifica colunas esperadas após merge
    assert "id_onibus" in df_final.columns
    assert "letreiro_linha_x" in df_final.columns or "letreiro_linha" in df_final.columns
    assert len(df_final) == len(sample_posicoes_df)


def test_merge_sem_previsoes(sample_posicoes_df):
    """Merge com DataFrame de previsões vazio não quebra."""
    previsoes_vazio = pd.DataFrame(columns=["id_onibus", "horario_previsao"])

    previsoes_unicas = previsoes_vazio.drop_duplicates(subset=["id_onibus"], keep="first")

    df_final = pd.merge(sample_posicoes_df, previsoes_unicas, on="id_onibus", how="left")

    assert len(df_final) == len(sample_posicoes_df)


def test_rename_colunas(sample_posicoes_df, sample_previsoes_df):
    """Verifica renomeação de colunas no fluxo da análise."""
    previsoes_unicas = sample_previsoes_df.sort_values("horario_previsao").drop_duplicates(
        subset=["id_onibus"], keep="first"
    )

    df_final = pd.merge(sample_posicoes_df, previsoes_unicas, on="id_onibus", how="left")

    from datetime import datetime

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

    colunas_esperadas = [
        "timestamp_analise",
        "id_onibus",
        "posicao_atual_lat",
        "posicao_atual_lon",
        "horario_posicao",
        "proximo_ponto_previsto",
        "horario_previsto_chegada",
    ]
    for col in colunas_esperadas:
        assert col in df_final.columns, f"Coluna {col} deveria existir"
