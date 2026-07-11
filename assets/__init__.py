from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)

from .checks import check_posicoes_bronze_silver, check_previsoes_bronze_silver
from .coleta import posicoes_sptrans, previsoes_sptrans
from .processamento import (
    compactar_posicoes,
    compactar_previsoes,
    expurgar_posicoes,
    expurgar_previsoes,
)

# --- Jobs (agrupamentos de assets para schedules) ---

coleta_posicoes_job = define_asset_job(
    name="coleta_posicoes_job",
    selection=AssetSelection.assets(posicoes_sptrans),
)

coleta_previsoes_job = define_asset_job(
    name="coleta_previsoes_job",
    selection=AssetSelection.assets(previsoes_sptrans),
)

compactacao_job = define_asset_job(
    name="compactacao_job",
    selection=AssetSelection.assets(compactar_posicoes, compactar_previsoes),
)

expurgo_job = define_asset_job(
    name="expurgo_job",
    selection=AssetSelection.assets(expurgar_posicoes, expurgar_previsoes),
)

# --- Schedules ---

posicoes_schedule = ScheduleDefinition(
    job=coleta_posicoes_job,
    cron_schedule="*/5 * * * *",  # a cada 5 minutos
    default_status=DefaultScheduleStatus.RUNNING,
)

previsoes_schedule = ScheduleDefinition(
    job=coleta_previsoes_job,
    cron_schedule="*/15 * * * *",  # a cada 15 minutos
    default_status=DefaultScheduleStatus.RUNNING,
)

compactacao_schedule = ScheduleDefinition(
    job=compactacao_job,
    cron_schedule="0 2 * * *",  # diariamente às 02:00
    default_status=DefaultScheduleStatus.RUNNING,
)

expurgo_schedule = ScheduleDefinition(
    job=expurgo_job,
    cron_schedule="0 3 * * *",  # diariamente às 03:00
    default_status=DefaultScheduleStatus.RUNNING,
)

# --- Definitions (ponto de entrada do Dagster) ---

defs = Definitions(
    assets=[
        posicoes_sptrans,
        previsoes_sptrans,
        compactar_posicoes,
        compactar_previsoes,
        expurgar_posicoes,
        expurgar_previsoes,
    ],
    schedules=[
        posicoes_schedule,
        previsoes_schedule,
        compactacao_schedule,
        expurgo_schedule,
    ],
    asset_checks=[
        check_posicoes_bronze_silver,
        check_previsoes_bronze_silver,
    ],
)
