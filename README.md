# 🚌 SPTrans Real-Time Public Transport Data Pipeline

[![CI](https://github.com/Roberton003/projeto_sptrans/actions/workflows/ci.yml/badge.svg)](https://github.com/Roberton003/projeto_sptrans/actions/workflows/ci.yml)

Pipeline de coleta, processamento e visualização de dados em tempo real do
transporte público de São Paulo via API Olho Vivo da SPTrans.

Processa ~555k posições de ônibus/dia em três camadas conceituais:

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| **Bronze** (raw) | SQLite ↔ PostgreSQL | Armazenamento idempotente, dados crus |
| **Silver** (analítico) | Parquet + DuckDB | Particionado por data, consultas rápidas |
| **Orquestração** | Dagster | Schedules, observabilidade, confiabilidade |

> 📖 Quer entender o projeto em profundidade? Veja o
> [Wiki](https://github.com/Roberton003/projeto_sptrans/wiki) com diagramas
> educativos, explicações camada a camada e boas práticas de engenharia de dados.

---

## Conceitos de Arquitetura

### Padrão Medallion (Bronze → Silver)

O pipeline segue uma variação do padrão **Medallion** (também chamado de
Multi-Hop Architecture), comum em lakehouses:

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  BRONZE  │ →  │  SILVER  │ →  │  GOLD    │
│ (cru)    │    │ (limpo)  │    │ (agreg.) │
└──────────┘    └──────────┘    └──────────┘
```

1. **Bronze** — dados crus como chegam da API SPTrans, persistidos com
   `INSERT OR IGNORE` para idempotência. Armazenamento: SQLite ou PostgreSQL.
2. **Silver** — dados transformados para análise: Parquet particionado por
   data, schema consistente, pronto para consultas com DuckDB.
3. **Gold** (em desenvolvimento) — agregações, métricas de qualidade,
   dashboards consolidados.

### Idempotência: o Princípio Fundamental

Cada estágio do pipeline pode ser reexecutado sem duplicar dados:

- **Inserção:** `INSERT OR IGNORE` + chave `UNIQUE` → reexecutar o coletor
  não gera duplicatas
- **Compactação:** `COPY TO ... OVERWRITE_OR_IGNORE` → rodar a exportação
  duas vezes para o mesmo dia produz Parquet idêntico
- **Expurgo:** opera por janela deslizante é reversível (backup)

### Abstração de Banco (`src/database.py`)

O módulo de banco expõe uma interface única que funciona tanto com SQLite
(desenvolvimento, testes) quanto PostgreSQL (produção, concorrência):

```python
from src.database import get_connection, insert_sql

# Funciona igual nos dois backends
with get_connection() as conn:
    cursor = conn.cursor()
    cursor.executemany(
        insert_sql("posicoes", columns),
        registros  # lista de tuplas
    )
```

A chave `DATABASE_URL` no ambiente decide o backend. Placeholders e sintaxe
de conflito são resolvidos automaticamente.

---

## Como os Dados Fluem — Visão Educativa

```
      API Olho Vivo SPTrans
              │
              ▼
    ┌─────────────────────┐
    │   COLTADOR (src/)   │  ← executado a cada 5 min (posições)
    │   requests + JSON   │     ou 15 min (previsões)
    └─────────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │   BRONZE STORAGE    │  ← INSERT OR IGNORE
    │   SQLite / Postgres │     chaves UNIQUE evitam duplicatas
    └─────────┬───────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  (compactação)  (expurgo)
   │ 02:00       │ 03:00
   ▼             ▼
┌──────────┐  ┌──────────┐
│  SILVER  │  │ janela   │ ← dados >7 dias viram
│  Parquet  │  │ quente   │   só Parquet
│  dt=YYYY  │  │ (Bronze) │
└─────┬────┘  └──────────┘
      │
      ▼
┌──────────┐    ┌──────────────┐
│ Análise  │    │  Dashboard   │
│ DuckDB   │    │  Streamlit   │
│ CLI      │    │  fallback    │
└──────────┘    └──────────────┘
```

### Passo a Passo

1. **Coleta** — `coleta_sptrans.py` autentica na API Olho Vivo, baixa posições
   de GPS das linhas configuradas, filtra apenas os letreiros de interesse e
   persiste com `INSERT OR IGNORE` no SQLite/PostgreSQL.
2. **Previsões** — `coleta_previsoes.py` faz o mesmo para previsões de chegada
   por linha.
3. **Compactação** — `compactar_parquet.py` lê o SQLite com DuckDB, particiona
   por data e escreve Parquet em `data/parquet/`.
4. **Expurgo** — `expurgar_sqlite.py` remove registros fora da janela
   deslizante (padrão 7 dias) para manter o banco leve.
5. **Análise** — `analise_onibus.py` consulta Parquet ou SQLite e gera
   métricas (ônibus agrupados, stuck buses, etc.).
6. **Dashboard** — `dashboard_sptrans.py` (Streamlit) carrega dados com
   fallback automático: tenta Parquet primeiro, SQLite se não existir.

---

## Arquitetura (Dagster)

```mermaid
flowchart TB
    subgraph BRONZE["Bronze — Raw Storage"]
        API[API Olho Vivo SPTrans]
        POS_COL[coleta_sptrans.py<br/>INSERT OR IGNORE]
        PREV_COL[coleta_previsoes.py<br/>INSERT OR IGNORE]
        SQLITE[(SQLite / PostgreSQL<br/>data/sptrans_data.db)]
        API -->|"coleta a cada 5min"| POS_COL
        API -->|"coleta a cada 15min"| PREV_COL
        POS_COL --> SQLITE
        PREV_COL --> SQLITE
    end

    subgraph SILVER["Silver — Camada Analítica"]
        COMPACTA[compactar_parquet.py<br/>DuckDB → Parquet<br/>OVERWRITE_OR_IGNORE]
        EXPURGO[expurgar_sqlite.py<br/>Janela deslizante 7d]
        PARQUET[(Parquet<br/>data/parquet/<br/>dt=YYYY-MM-DD)]
        SQLITE --> COMPACTA
        SQLITE --> EXPURGO
        COMPACTA --> PARQUET
    end

    subgraph GOLD["Gold — Consumo"]
        ANALISE[analise_onibus.py<br/>--mode parquet/sqlite]
        DASHBOARD[dashboard_sptrans.py<br/>Streamlit + DuckDB]
        PARQUET --> ANALISE
        PARQUET --> DASHBOARD
        SQLITE -.->|fallback| ANALISE
        SQLITE -.->|fallback| DASHBOARD
    end

    subgraph ORQUESTRAÇÃO["Orquestração — Dagster"]
        S1[Schedule */5<br/>posicoes_sptrans]
        S2[Schedule */15<br/>previsoes_sptrans]
        S3[Schedule 0 2<br/>compactar_*]
        S4[Schedule 0 3<br/>expurgar_*]
        S1 --> POS_COL
        S2 --> PREV_COL
        S3 --> COMPACTA
        S4 --> EXPURGO
    end
```

---

## Estrutura do Projeto

```
.
├── assets/                 # Assets Dagster (orquestração)
│   ├── __init__.py         # Definitions + schedules
│   ├── coleta.py           # posicoes_sptrans, previsoes_sptrans
│   └── processamento.py    # compactar_*, expurgar_*
├── src/                    # Código-fonte
│   ├── coleta_sptrans.py           # Coleta posições (batch)
│   ├── coleta_previsoes.py         # Coleta previsões (batch)
│   ├── inicializar_banco.py        # Criação de schema + índices
│   ├── compactar_parquet.py        # SQLite → Parquet (DuckDB)
│   ├── analise_onibus.py           # Análise de linhas/ônibus
│   ├── dashboard_sptrans.py        # Dashboard Streamlit
│   ├── expurgar_sqlite.py          # Expurgo de janela deslizante
│   ├── migrar_dedup.py             # Migração one-shot dedup
│   └── database.py                 # Abstração SQLite ↔ PostgreSQL
├── tests/                  # Testes (62 ativos + 5 PostgreSQL condicionais)
├── .github/workflows/      # CI (ruff lint + pytest)
├── config/
│   ├── config.ini.template          # Template de configuração
│   └── config.ini                   # Config local (gitignorado)
├── data/
│   ├── sptrans_data.db              # SQLite principal
│   └── parquet/                     # Parquet particionado por dt=
├── workspace.yaml          # Code location do Dagster
├── docker-compose.yml      # 5 serviços (inclui dagster + postgres)
├── Dockerfile
├── Makefile                # test, lint, install, clean
├── pyproject.toml          # ruff + pytest config
└── requirements*.txt       # Dependências
```

---

## Scripts

### Coletores

Os coletores escrevem diretamente no banco com `INSERT OR IGNORE`, usando
índices `UNIQUE` para garantir idempotência mesmo em reexecuções:

| Script | Função | Execução sugerida |
| ------ | ------ | ----------------- |
| `coleta_sptrans.py` | Coleta posições de GPS dos ônibus | `cron` a cada 3-5 min |
| `coleta_previsoes.py` | Coleta previsões de chegada por linha | `cron` a cada 10-15 min |
| `inicializar_banco.py` | Cria schema + índices UNIQUE | Antes da primeira coleta |

### Camada Analítica

| Script | Função |
| ------ | ------ |
| `compactar_parquet.py` | Exporta SQLite → Parquet particionado por data via DuckDB |
| `analise_onibus.py` | Análise agnóstica: `--mode parquet` (DuckDB) ou `sqlite` |
| `dashboard_sptrans.py` | Dashboard Streamlit com fallback Parquet→SQLite |
| `expurgar_sqlite.py` | Expurga registros fora da janela deslizante (padrão 7 dias) |

### Manutenção

| Script | Função |
| ------ | ------ |
| `migrar_dedup.py` | Remove duplicatas existentes e aplica UNIQUE INDEX (one-shot) |
| `database.py` | Abstração de banco: SQLite (dev) ↔ PostgreSQL (prod) |

---

## Schema do Banco

### `posicoes`

| Coluna | Tipo | Descrição |
| ------ | ---- | --------- |
| `timestamp_coleta` | DATETIME | ISO 8601 — quando os dados foram baixados |
| `id_onibus` | INTEGER | Identificador do veículo |
| `letreiro_linha` | TEXT | Letreiro da linha (ex: `8000-10`) |
| `latitude` / `longitude` | REAL | Coordenadas GPS |
| `timestamp_posicao` | DATETIME | Hora do GPS (enviada pelo ônibus) |

**Chave natural (dedup):** `(timestamp_coleta, id_onibus)`

### `previsoes`

| Coluna | Tipo | Descrição |
| ------ | ---- | --------- |
| `timestamp_coleta` | DATETIME | ISO 8601 — quando os dados foram baixados |
| `id_linha` | INTEGER | Código da linha |
| `id_onibus` | INTEGER | Veículo |
| `id_parada` | INTEGER | Ponto de parada |
| `horario_previsao` | DATETIME | Previsão de chegada |

**Chave natural (dedup):** `(timestamp_coleta, id_linha, id_onibus, id_parada, horario_previsao)`

---

## Setup

### Backend de armazenamento: SQLite (padrão) vs PostgreSQL

O pipeline suporta dois backends de armazenamento, controlados pela
variável de ambiente `DATABASE_URL`:

| Backend | DATABASE_URL | Uso |
|---------|-------------|-----|
| **SQLite** (padrão) | Não definir | Desenvolvimento local, testes |
| **PostgreSQL** | `postgresql://user:pass@host:5432/db` | Produção, concorrência |

O módulo `src/database.py` abstrai a diferença: `INSERT OR IGNORE` (SQLite)
vs `INSERT ... ON CONFLICT DO NOTHING` (PostgreSQL), placeholders `?` vs `%s`.

### Com SQLite (padrão)

```bash
# 1. Configurar token
cp config/config.ini.template config/config.ini
# Editar config/config.ini com seu token SPTrans

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Inicializar banco + schema
python src/inicializar_banco.py

# 4. Coletar dados
python src/coleta_sptrans.py         # posições
python src/coleta_previsoes.py        # previsões
```

### Com PostgreSQL (produção)

```bash
# 1. Iniciar PostgreSQL (via Docker)
docker compose up -d postgres

# 2. Inicializar banco + schema no PostgreSQL
DATABASE_URL="postgresql://sptrans:sptrans_local@localhost:5432/sptrans" \
  python src/inicializar_banco.py

# 3. Coletar dados apontando para PostgreSQL
DATABASE_URL="postgresql://sptrans:sptrans_local@localhost:5432/sptrans" \
  python src/coleta_sptrans.py

# 4. (Opcional) Migrar dados existentes do SQLite para PostgreSQL
DATABASE_URL="postgresql://sptrans:sptrans_local@localhost:5432/sptrans" \
  python src/migrar_postgres.py
```

### Camada analítica (Parquet + DuckDB)

```bash
pip install duckdb pyarrow
python src/compactar_parquet.py              # SQLite → Parquet particionado
python src/compactar_parquet.py --date YYYY-MM-DD  # dia específico
python src/analise_onibus.py --mode parquet
```

### Dashboard

```bash
streamlit run src/dashboard_sptrans.py
```

### Expurgo (janela deslizante)

```bash
python src/expurgar_sqlite.py           # expurga >7 dias
python src/expurgar_sqlite.py --dias 30 # expurga >30 dias
python src/expurgar_sqlite.py --dry-run # simula sem deletar
```

O script respeita `DATABASE_URL` — se definido, expurga no PostgreSQL.

---

## Orquestração (Dagster)

O pipeline é orquestrado por **Dagster** com 6 assets e 4 schedules:

| Asset | Schedule | Descrição |
|-------|----------|-----------|
| `posicoes_sptrans` | `*/5 * * * *` | Coleta posições dos ônibus |
| `previsoes_sptrans` | `*/15 * * * *` | Coleta previsões de chegada |
| `compactar_posicoes` | `0 2 * * *` | SQLite → Parquet (posições) |
| `compactar_previsoes` | `0 2 * * *` | SQLite → Parquet (previsões) |
| `expurgar_posicoes` | `0 3 * * *` | Expurga posições >7 dias |
| `expurgar_previsoes` | `0 3 * * *` | Expurga previsões >7 dias |

Dependências entre assets:

```
posicoes_sptrans ──→ compactar_posicoes ──→ expurgar_posicoes
previsoes_sptrans ──→ compactar_previsoes ──→ expurgar_previsoes
```

### Iniciar o Dagster

```bash
docker compose up dagster
# UI em http://localhost:3000
```

### Desenvolvimento local (sem Docker)

```bash
pip install dagster dagster-webserver
dagster dev -w workspace.yaml
```

---

## Qualidade e CI

| Gate | Comando | Status |
| ---- | ------- | ------ |
| Lint | `make lint` ou `ruff check src/ tests/` | ✅ 0 violações |
| Testes | `make test` ou `pytest tests/ -q` | ✅ 62/62 + 5 skipped (PostgreSQL¹) |
| CI | GitHub Actions (push/PR) | [![CI](https://github.com/Roberton003/projeto_sptrans/actions/workflows/ci.yml/badge.svg)](https://github.com/Roberton003/projeto_sptrans/actions/workflows/ci.yml) |

¹ **Testes PostgreSQL:** 5 testes em `tests/test_postgres.py` rodam apenas quando
`DATABASE_URL` está configurada. Com PostgreSQL real via Docker, a suite completa
fica em **67/67 passando**. O CI roda sem PostgreSQL, por isso aparecem 5 skipped.

### Modelo de dados — idempotência

- Coletores usam `INSERT OR IGNORE` (SQLite) / `ON CONFLICT DO NOTHING` (PostgreSQL) com `UNIQUE INDEX`
- Camada de banco (`src/database.py`) abstrai diferenças de sintaxe entre backends
- Compactação Parquet usa `OVERWRITE_OR_IGNORE` para reexecução segura
- Expurgo é reversível via backup

---

## 🔍 Linhagem e Quality Gates (Plano 004)

A partir do Plano 004, o pipeline passou a registrar **linhagem leve** e aplicar **verificações de integridade entre camadas** automaticamente.

### Visão: O que cada execução registra

```mermaid
flowchart LR
    A[Asset Dagster] -->|row_count| B[MetadataValue.int]
    A -->|INSERT| C[lineage_audit table]
    A -->|AssetCheck| D{Reconciliação<br/>Bronze ↔ Silver}
    D -->|OK| E[passed=True<br/>alarme silencioso]
    D -->|>5% diff| F[passed=False<br/>alarme visível]
    C -->|SELECT| G[Auditoria SQL]
    B -->|UI| H[Dagster Web UI]
```

### 1. Linhagem: tabela `lineage_audit`

Cada execução de asset grava **1 linha** em `lineage_audit` (SQLite/PostgreSQL):

```sql
CREATE TABLE lineage_audit (
    id INTEGER PRIMARY KEY,
    asset_name TEXT NOT NULL,        -- ex: 'compactar_posicoes'
    table_name TEXT NOT NULL,        -- ex: 'posicoes'
    layer TEXT NOT NULL,             -- 'bronze' ou 'silver'
    run_timestamp TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    status TEXT NOT NULL             -- 'ok', 'warning', 'error'
);
```

**Por que é importante:** se um dia o dashboard mostrar números estranhos, a primeira pergunta é *"o pipeline escreveu dados errados ou a fonte mudou?"*. Com a tabela `lineage_audit`, você responde em segundos:

```sql
-- Última execução de cada asset
SELECT asset_name, layer, row_count, status, run_timestamp
FROM lineage_audit
ORDER BY run_timestamp DESC
LIMIT 10;
```

### 2. Schema Contracts: `src/contracts.py`

Quatro Pydantic models formalizam o **schema esperado** de cada camada com restrições automáticas:

| Model | Camada | Restrições principais |
|-------|--------|----------------------|
| `PosicaoBronze` | Bronze | `id_onibus > 0`, `lat ∈ [-90, 90]`, `lon ∈ [-180, 180]`, `letreiro_linha ≤ 20 chars` |
| `PrevisaoBronze` | Bronze | `id_linha > 0`, `id_onibus > 0`, `horario_previsao ≤ 30 chars` |
| `PosicaoSilver` | Silver | Tudo de Bronze + `dt` no formato `YYYY-MM-DD` (partição) |
| `PrevisaoSilver` | Silver | Tudo de Bronze + `dt` no formato partição |

**Como usar:**

```python
from src.contracts import PosicaoBronze, validar_lote

# Validação unitária (lança ValidationError se inválido)
rec = PosicaoBronze(timestamp_coleta=..., id_onibus=12345, latitude=-23.55, longitude=-46.63)

# Validação em lote (retorna lista de erros, NÃO aborta)
erros = validar_lote(PosicaoBronze, registros_dict)
if erros:
    logger.warning("%d registros rejeitados pelo contrato", len(erros))
```

### 3. Quality Gates: Dagster AssetCheck

Dois `AssetCheck` reconciliam Bronze ↔ Silver após cada compactação, com **tolerância de 5%**:

| Check | Verifica | Tolerância |
|-------|----------|------------|
| `check_posicoes_bronze_silver` | `count(posicoes)` SQLite ≈ `count(*)` Parquet | ±5% |
| `check_previsoes_bronze_silver` | `count(previsoes)` SQLite ≈ `count(*)` Parquet | ±5% |

**Exemplo de código (`assets/checks.py`):**

```python
@asset_check(asset=compactar_posicoes)
def check_posicoes_bronze_silver():
    bronze = _contagem_sqlite("posicoes")
    silver = _contagem_parquet("posicoes")
    diff_pct = abs(bronze - silver) / max(bronze, 1) * 100
    return AssetCheckResult(
        passed=diff_pct <= 5,
        description=f"Bronze={bronze} Silver={silver} diff={diff_pct:.1f}%"
    )
```

**Por que não-bloqueante:** dado ruim é logado e registrado em `lineage_audit` com `status='warning'`, mas o pipeline continua. Se a divergência for sistemática (>5% consistente), vira issue a investigar — alarme, não barreira.

### Decisões do Plano 004

| Decisão | Alternativa rejeitada | Motivo |
|---------|----------------------|--------|
| `MetadataValue.int` nativo do Dagster | OpenLineage + Marquez | Stack pesada (Java/Kafka/DB) para 2 tabelas |
| `lineage_audit` no mesmo banco | Catálogo externo (DataHub) | Mantém auditoria na mesma transação; sem dependência extra |
| Pydantic para contratos | Great Expectations / Soda | Já temos Pydantic; cobre o caso com zero dependência nova |
| AssetCheck não-bloqueante | Bloquear pipeline em falha | Falha silenciosa em log > pipeline travado |

---

## Aprendizados de Engenharia

Este projeto ilustra conceitos fundamentais de engenharia de dados:

| Conceito | Como é aplicado aqui |
|----------|---------------------|
| **Idempotência** | `INSERT OR IGNORE` + chaves UNIQUE → reexecutar é seguro |
| **Padrão Medallion** | Bronze (raw) → Silver (Parquet) → Gold (dashboards) |
| **Abstração de backend** | `src/database.py` troca SQLite ↔ PostgreSQL sem alterar coletores |
| **Particionamento** | Parquet particionado por `dt=` → consultas escaneiam menos dados |
| **Janela deslizante** | Expurgo mantém o banco leve; dados históricos ficam em Parquet |
| **Orquestração declarativa** | Dagster define o que executa, quando e em que ordem |
| **Fallback resiliente** | Dashboard tenta Parquet primeiro, SQLite se não disponível |
| **CI/CD** | GitHub Actions + ruff + pytest a cada push |
| **Linhagem de dados** | Tabela `lineage_audit` + `MetadataValue.int` → rastreabilidade de cada execução |
| **Schema contracts** | Pydantic models em `src/contracts.py` validam tipos e ranges automaticamente |
| **Quality gates** | `AssetCheck` reconcilia Bronze↔Silver com tolerância 5% (alarme, não barreira) |

---

## Limitações

1. **API pública não autenticada:** desde jun/2025 a SPTrans desativou a
   autenticação por token — a API está aberta, o que reduz a barreira de
   entrada mas pode mudar sem aviso.
2. **SQLite como singleton (legado):** configurar `DATABASE_URL` para PostgreSQL
   elimina a limitação de concorrência.
3. **Parquet não é fonte de verdade:** é uma projeção do SQLite para
   performance analítica. Em caso de divergência, o SQLite é a autoridade.
4. **Linhagem leve (Plano 004):** temos `lineage_audit` e AssetChecks, mas
   não é um catálogo OpenLineage/Marquez completo. Para ambientes com
   múltiplos pipelines, considere integração com DataHub.
5. **DuckDB não é multi-usuário:** DuckDB é embarcado; para serving
   analítico concorrente, migrar para MotherDuck ou PostgreSQL.
6. **Docker legado:** a configuração Docker existe mas não reflete as
   features de Parquet/DuckDB. Para usar a stack completa, prefira
   execução nativa.
