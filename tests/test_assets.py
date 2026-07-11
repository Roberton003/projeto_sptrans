"""Testes dos assets Dagster: parsing, schedules, dependências."""

from dagster import AssetKey, Definitions


def test_assets_load():
    """Assets carregam sem erro de parsing."""
    from assets import defs

    assert isinstance(defs, Definitions)


def test_asset_keys():
    """Os 6 assets esperados estão registrados."""
    from assets import defs

    g = defs.resolve_asset_graph()
    keys = {str(k) for k in g.get_all_asset_keys()}
    expected = {
        "AssetKey(['posicoes_sptrans'])",
        "AssetKey(['previsoes_sptrans'])",
        "AssetKey(['compactar_posicoes'])",
        "AssetKey(['compactar_previsoes'])",
        "AssetKey(['expurgar_posicoes'])",
        "AssetKey(['expurgar_previsoes'])",
    }
    assert keys == expected, f"Esperado {expected}, obtido {keys}"


def test_asset_dependencies():
    """Dependências entre assets estão corretas."""
    from assets import defs

    g = defs.resolve_asset_graph()

    # compactar_posicoes depende de posicoes_sptrans
    cp = g.get(AssetKey(["compactar_posicoes"]))
    cp_parents = {str(p) for p in cp.parent_keys}
    assert "AssetKey(['posicoes_sptrans'])" in cp_parents, (
        f"compactar_posicoes deve depender de posicoes_sptrans; pais = {cp_parents}"
    )

    # compactar_previsoes depende de previsoes_sptrans
    cp2 = g.get(AssetKey(["compactar_previsoes"]))
    cp2_parents = {str(p) for p in cp2.parent_keys}
    assert "AssetKey(['previsoes_sptrans'])" in cp2_parents

    # expurgar_posicoes depende de compactar_posicoes (mas não de posicoes_sptrans direto)
    ep = g.get(AssetKey(["expurgar_posicoes"]))
    ep_parents = {str(p) for p in ep.parent_keys}
    assert "AssetKey(['compactar_posicoes'])" in ep_parents
    # não deve depender direto de posicoes_sptrans
    assert "AssetKey(['posicoes_sptrans'])" not in ep_parents


def test_schedules_exist():
    """4 schedules registrados."""
    from assets import defs

    schedules = list(defs.schedules)
    assert len(schedules) == 4, f"Esperado 4 schedules, obtido {len(schedules)}"


def test_schedules_cron_valid():
    """Todos os cron_schedule são expressões cron válidas (5 campos)."""
    from assets import defs

    for s in defs.schedules:
        cron = s.cron_schedule
        assert isinstance(cron, str), f"cron_schedule de {s.name} não é string"
        parts = cron.split()
        assert len(parts) == 5, f"cron_schedule '{cron}' de {s.name} tem {len(parts)} campos (esperado 5)"


def test_schedules_names():
    """Schedules têm os nomes esperados."""
    from assets import defs

    names = {s.name for s in defs.schedules}
    expected = {
        "coleta_posicoes_job_schedule",
        "coleta_previsoes_job_schedule",
        "compactacao_job_schedule",
        "expurgo_job_schedule",
    }
    assert names == expected, f"Esperado {expected}, obtido {names}"


def test_jobs_exist():
    """4 jobs customizados + 1 implícito registrados."""
    from assets import defs

    jobs = list(defs.resolve_all_job_defs())
    # 4 custom + 1 implícito (__ASSET_JOB)
    assert len(jobs) >= 4, f"Esperado >=4 jobs, obtido {len(jobs)}"


def test_asset_groups():
    """Assets organizados nos grupos 'coleta' e 'processamento'."""
    from assets import defs

    g = defs.resolve_asset_graph()
    groups = {}
    for key in g.get_all_asset_keys():
        node = g.get(key)
        groups.setdefault(node.group_name, set()).add(str(key))

    assert "coleta" in groups, "Grupo 'coleta' não encontrado"
    assert "processamento" in groups, "Grupo 'processamento' não encontrado"
    assert groups["coleta"] == {
        "AssetKey(['posicoes_sptrans'])",
        "AssetKey(['previsoes_sptrans'])",
    }
    assert groups["processamento"] == {
        "AssetKey(['compactar_posicoes'])",
        "AssetKey(['compactar_previsoes'])",
        "AssetKey(['expurgar_posicoes'])",
        "AssetKey(['expurgar_previsoes'])",
    }
