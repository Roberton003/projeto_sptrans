"""
Contratos de dados formais para cada camada do pipeline.

Define schemas esperados (Bronze/Silver) como Pydantic models,
validáveis em tempo de pipeline com pydantic.model_validate().

Uso:
    from src.contracts import PosicaoBronze, validar_lote

    erros = validar_lote(PosicaoBronze, lista_de_dicts)
    if erros:
        logger.warning("%s registros rejeitados por schema", len(erros))
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ─── Bronze (dado raw do SQLite, exatamente como chega da API) ───


class PosicaoBronze(BaseModel):
    """Registro de posição de GPS — camada Bronze (SQLite / API original)."""

    timestamp_coleta: datetime
    id_onibus: int = Field(gt=0, description="Identificador do veículo")
    letreiro_linha: str | None = Field(None, max_length=20)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timestamp_posicao: datetime | None = None

    model_config = {
        "from_attributes": True,
        "extra": "ignore",
    }


class PrevisaoBronze(BaseModel):
    """Registro de previsão de chegada — camada Bronze (SQLite)."""

    timestamp_coleta: datetime
    id_linha: int = Field(gt=0)
    id_onibus: int = Field(gt=0)
    id_parada: int | None = None
    horario_previsao: str | None = Field(None, max_length=30)

    model_config = {
        "from_attributes": True,
        "extra": "ignore",
    }


# ─── Silver (dado consolidado em Parquet) ───


class PosicaoSilver(BaseModel):
    """Registro de posição consolidado — camada Silver (Parquet)."""

    timestamp_coleta: datetime
    id_onibus: int = Field(gt=0)
    letreiro_linha: str | None = Field(None, max_length=20)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timestamp_posicao: datetime | None = None
    dt: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Partição (YYYY-MM-DD)")

    model_config = {
        "from_attributes": True,
        "extra": "ignore",
    }


class PrevisaoSilver(BaseModel):
    """Registro de previsão consolidado — camada Silver (Parquet)."""

    timestamp_coleta: datetime
    id_linha: int = Field(gt=0)
    id_onibus: int = Field(gt=0)
    id_parada: int | None = None
    horario_previsao: str | None = Field(None, max_length=30)
    dt: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="Partição (YYYY-MM-DD)")

    model_config = {
        "from_attributes": True,
        "extra": "ignore",
    }


# ─── Utilitários ───


def validar_lote(model_class: type[BaseModel], registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valida uma lista de dicts contra um Pydantic model.

    Args:
        model_class: Classe Pydantic (ex: PosicaoBronze).
        registros: Lista de dicionários com os campos esperados.

    Returns:
        Lista de registros que falharam validação (vazia se todos OK).
    """
    erros: list[dict[str, Any]] = []
    for i, rec in enumerate(registros):
        try:
            model_class(**rec)  # type: ignore[call-overload]
        except Exception as exc:
            erros.append({"indice": i, "registro": rec, "erro": str(exc)})
    return erros
