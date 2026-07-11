# Plano 004 — Linhagem + Verificações de Integridade entre Camadas

> **Classificação:** T3-HIGH — multi-arquivo, schema/qualidade, cross-pipeline
> **Skills carregadas:** task-router, data-engineering, data-contracts-protocol, data-quality-validator, data-engineering-gates, write-implementation-plan
> **Heurística aplicada:** airflow3_009 — gate de quality check entre transformação e publicação

---

## 1. Contexto

O pipeline hoje tem 6 assets Dagster que fluem:

```
Bronze (SQLite)                              Silver (Parquet)
  posicoes_sptrans ────→ compactar_posicoes ────→ expurgar_posicoes
  previsoes_sptrans ────→ compactar_previsoes ────→ expurgar_previsoes
```

**O que não existe:**
- ❌ **Linhagem:** nenhum registro de quantos registros entram/saem de cada camada
- ❌ **Verificação entre camadas:** `compactar_posicoes` roda, mas ninguém confere se Parquet tem os mesmos registros que SQLite
- ❌ **Schema contract:** tabelas existem mas sem validação formal de tipos/colunas em tempo de pipeline
- ❌ **Rastreabilidade:** se um dado errado chegar ao dashboard, não há como rastrear de volta ao registro original

---

## 2. Objetivo

Implementar **linhagem leve** + **verificações de integridade entre camadas** com custo de manutenção mínimo, usando o que já temos:

| O quê | Como | Onde |
|-------|------|------|
| 📊 Contagem por camada | Dagster metadata (`MetadataValue.int`) + tabela `lineage_audit` | assets/coleta.py, assets/processamento.py |
| ✅ Schema contract | Pydantic models por camada, validados via `pydantic.model_validate` | src/contracts.py (novo) |
| 🔗 Verificação Bronze→Silver | Row count + amostra hash entre SQLite e Parquet | assets/processamento.py |
| 🚦 Quality gates | Dagster `AssetCheck` — falha não bloqueia, mas loga + persiste | assets/checks.py (novo) |
| 📖 Visibilidade | README + Wiki atualizados com diagrama de linhagem | README.md, Wiki |

---

## 3. Escopo

### Dentro
- [x] Tabela `lineage_audit` no SQLite: `id, asset_name, table_name, layer, run_timestamp, row_count, status`
- [x] Metadata de row_count em cada asset via Dagster `MetadataValue.int`
- [x] Pydantic `DataContract` por camada (schema esperado + regras)
- [x] Asset check de contagem Bronze vs Silver após compactação
- [x] Testes unitários para contratos e checks
- [x] Atualizar Wiki com diagrama de linhagem + seção de qualidade

### Fora
- ❌ OpenLineage/Marquez/DataHub (overhead para este porte)
- ❌ Column-level lineage granulado
- ❌ Quarantine automática (dados ruins param no log, não no pipeline — escape clause da heurística)
- ❌ UI de linhagem interativa

---

## 4. Alternativas Rejeitadas

| Alternativa | Motivo da Rejeição |
|------------|-------------------|
| OpenLineage + Marquez | Stack pesada (Java, Kafka, DB externo) para um projeto de 2 tabelas |
| Great Expectations | Overhead de config e dependências; Pydantic + SQL cobre o necessário |
| Tabela de lineage separada (PostgreSQL) | SQLite já está versionado e presente; adicionar outro banco seria complexidade sem ganho |

---

## 5. Decisões

| Decisão | Motivo |
|---------|--------|
| Usar `MetadataValue.int` nativo do Dagster | Sem dependência externa, visível na UI do Dagster |
| Audit trail em `lineage_audit` no SQLite | Histórico consultável por SQL, independente de Dagster |
| Pydantic como schema contract | Já usado no projeto, sem dependência nova |
| AssetCheck no Dagster (não blokante) | Dado ruim é logado mas pipeline não aborta — alarme, não barreira |

---

## 6. Etapas

### Fase 1 — Schema Contracts (`src/contracts.py`)

**Arquivos:**
- Create: `src/contracts.py`
- Modify: `tests/conftest.py`

**Tarefa:** Definir Pydantic models para cada camada com regras de validação.

```python
# src/contracts.py
from pydantic import BaseModel, Field
from datetime import datetime

class PosicaoBronze(BaseModel):
    """Registro raw da API Olho Vivo — camada Bronze."""
    timestamp_coleta: datetime
    id_onibus: int = Field(gt=0)
    letreiro_linha: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp_posicao: datetime | None = None

class PrevisaoBronze(BaseModel):
    """Previsão raw — camada Bronze."""
    timestamp_coleta: datetime
    id_linha: int = Field(gt=0)
    id_onibus: int = Field(gt=0)
    id_parada: int | None = None
    horario_previsao: str | None = None

class PosicaoSilver(BaseModel):
    """Registro consolidado em Parquet — camada Silver."""
    timestamp_coleta: datetime
    id_onibus: int = Field(gt=0)
    letreiro_linha: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp_posicao: datetime | None = None
    dt: str  # partição (YYYY-MM-DD)
```

**Validação:**
- `pytest tests/test_contracts.py -q` — 3+ testes validando cada model

### Fase 2 — Tabela `lineage_audit` + Metadata

**Arquivos:**
- Modify: `src/database.py`
- Modify: `assets/coleta.py`
- Modify: `assets/processamento.py`

**Tarefa:** Adicionar tabela `lineage_audit` e registrar metadata de row_count.

**`src/database.py`:**
- Adicionar `CREATE TABLE IF NOT EXISTS lineage_audit (...)` nos `_schema_sqlite()` e `_schema_postgres()`
- Função `registrar_linhagem(asset_name, table_name, layer, row_count, status)` que faz INSERT

**`assets/coleta.py`:**
- Cada asset retorna `Output(value, metadata={"row_count": MetadataValue.int(n)})`
- Após coleta, ler `SELECT count(*)` da tabela e registrar em `lineage_audit`

**`assets/processamento.py`:**
- `compactar_*` assets: registrar contagem SQLite (antes) e Parquet (depois) em metadata + audit
- `expurgar_*` assets: registrar quantos registros foram removidos

**Validação:**
- `pytest tests/ -k "linhagem" -q` — novos testes
- `python3 -c "from assets import defs; ..."` — assets carregam sem erro

### Fase 3 — Quality Gates (Dagster AssetCheck)

**Arquivos:**
- Create: `assets/checks.py`
- Modify: `assets/__init__.py`

**Tarefa:** Adicionar `AssetCheck` para verificar integridade entre camadas.

**`assets/checks.py`:**
```python
@asset_check(asset=compactar_posicoes)
def check_posicoes_bronze_silver(context: CheckContext):
    """Verifica se contagem Parquet >= 95% da contagem SQLite (tolerância para latência)."""
    ...
    if abs_diff_pct > 5:
        return AssetCheckResult(passed=False, description="Diferença >5% entre Bronze e Silver")
    return AssetCheckResult(passed=True, description=f"OK: {bronze} → {silver} registros")
```

**`assets/__init__.py`:**
- Adicionar `asset_checks=[...]` na Definitions

**Validação:**
- `pytest tests/test_checks.py -q` — 3+ testes
- `python -c "from assets import defs; checks = list(defs.asset_checks)"`

### Fase 4 — Testes

**Arquivos:**
- Create: `tests/test_contracts.py`
- Create: `tests/test_linhagem.py`
- Create: `tests/test_checks.py`

**Tarefa:** Testes para cada novo componente.

- `test_contracts.py`: validar schemas, campos obrigatórios, tipos, valores inválidos
- `test_linhagem.py`: testar `registrar_linhagem()`, metadata nos assets mockados
- `test_checks.py`: testar check de reconciliação com dados sintéticos

### Fase 5 — Documentação (Wiki + README)

**Arquivos:**
- Modify: Wiki pages (Arquitetura, Fluxo-de-Dados, Componentes)

**Tarefa:** Adicionar seção de linhagem e qualidade.

- Arquitetura.md: diagrama de linhagem (Bronze→Silver→Gold com setas de verificação)
- Fluxo-de-Dados.md: incluir quality gates no passo a passo
- Componentes.md: contracts.py, checks.py, lineage_audit

---

## 7. Critérios de Aceite

- [ ] `pytest tests/ -q` — 0 failures (testes existentes + novos)
- [ ] `ruff check src/ assets/ tests/` — 0 violações nos arquivos modificados/criados
- [ ] `python3 -c "from assets import defs"` — carrega sem erro
- [ ] `from src.contracts import PosicaoBronze, PrevisaoBronze, PosicaoSilver` — sem erro
- [ ] `from assets.checks import *` — sem erro

---

## 8. STOP Conditions

- [ ] `pytest tests/test_contracts.py -q` — 0 failures
- [ ] `python3 -c "from assets import defs; assert len(list(defs.asset_checks)) >= 1"` — ao menos 1 check registrado
- [ ] `grep -c "lineage_audit" src/database.py` — pelo menos 1 ocorrência

---

## 9. Risco e Rollback

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| AssetCheck falhar com dados reais (tolerância muito baixa) | Média | Usar 5% de tolerância e `passed=False` sem abortar |
| Tabela lineage_audit crescer sem expurgo | Baixa | ~365 registros/ano por asset (2KB) — irrelevante |
| Mudança de schema quebrar contrato Pydantic | Baixa | Teste no CI pega antes do merge |

**Rollback:** reverter `git revert` dos commits de cada fase.

---

## 10. Processing Context

### ◈ Processing Context

- ✦ **Lead Agent:** OpenCode Chief Engineer
- ▫ **Supporting Agents:** Este trabalho foi produzido sem subagentes invocados.
- ⌥ **Skills Used:** task-router, data-engineering, data-contracts-protocol, data-quality-validator, data-engineering-gates, write-implementation-plan
- ☄ **Knowledge Sources:** Código-fonte atual (assets/, src/, tests/), heurística airflow3_009 (data quality gate)
- ☱ **Files Analyzed:** assets/__init__.py, assets/coleta.py, assets/processamento.py, src/database.py, src/compactar_parquet.py, tests/test_assets.py
- ◬ **Decision Complexity:** T3-HIGH — schema contracts + lineage + quality gates em pipeline existente
- 🤖 **Model Used:** DeepSeek V4 Flash Go
- 🔁 **Model Recommendation for Next Step:** DeepSeek V4 Flash Go (workhorse) para implementação; a complexidade está no design, não na execução
- 💰 **Budget Notes:** 5 fases, ~12 arquivos alterados. Budget T3 sem teto de steps
- ✅ **Validations:** pytest, ruff, dagster resolve_asset_graph, import checks
- ⚠️ **Not Executed:** OpenLineage/Marquez (fora de escopo), column-level lineage (fora de escopo)
