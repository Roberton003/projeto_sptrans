# Plano 003 — Orquestração: Complementos e PostgreSQL

> **PRD base:** `docs/plans/PRD_orquestracao.md`
> **Status dos Épicos 1-3:** ✅ Concluídos e verificados
> **Modelo:** T3-LOW — planos paralelos, sem interdependência

---

## Contexto

Épicos 1-3 do PRD de orquestração foram executados e verificados:
6 assets, 4 schedules, 4 jobs carregados via Dagster. Restam:

- **Épico 4:** Testes dos assets (parsing, dependências, schedules)
- **Épico 5:** Completar documentação no README
- **Fora do PRD:** Plano de migração PostgreSQL (Estágio 2 do Roadmap)

---

## Objetivo

Concluir PRD de orquestração e preparar roteiro para PostgreSQL,
**sem executar a migração** — apenas plano detalhado para aprovação.

---

## Escopo

### Incluído
- `tests/test_assets.py` — validação de parsing, schedules, dependências
- CI atualizado com dependência `dagster` para os testes de asset
- README com seção de orquestração finalizada + badge CI
- Plano de migração PostgreSQL (análise, riscos, trade-offs, steps)

### Fora de Escopo
- **Executar migração PostgreSQL** — apenas o plano (aprovado = próximo PRD)
- Deploy em nuvem (Estágio 4)
- dbt/transformações (Estágio 3)
- Streaming/Kafka

---

## Alternativas Rejeitadas

### Airflow (vs Dagster)
Já decidido no PRD: Dagster é superior para este caso (modelo de assets,
testabilidade nativa, skill disponível no harness).

### AsyncIO/Streaming (vs PostgreSQL)
Descartado no PRD anterior — API Olho Vivo é REST polling, não streaming.

---

## Decisões

| Decisão | Motivo | Premissa Crítica |
|---------|--------|-----------------|
| Testes de asset em pytest puro | Dagster expõe `Definitions` que pytest valida sem precisar de `dagster-test` | Dagster 1.13 mantém API de `Definitions` estável |
| PostgreSQL como Estágio 2 | SQLite é singleton; próximo gargalo real é concorrência de escrita | Volume continuará abaixo de 1M linhas/dia |
| `asyncpg` + `psycopg2` | Driver mais performático para PostgreSQL async | Sem necessidade de ORM (SQLAlchemy adicionaria complexidade sem ganho) |

---

## Plano: Épico 4 — Testes de Orquestração

### Tarefa 4.1: Criar `tests/test_assets.py`

**Arquivo:** `tests/test_assets.py`

Testes a implementar:

1. `test_assets_load` — `from assets import defs` → `defs.get_asset_graph()` não levanta exceção
2. `test_asset_keys` — `defs.get_asset_graph().get_all_asset_keys()` contém os 6 assets esperados
3. `test_asset_dependencies` — validar upstream/downstream (ex: `compactar_posicoes` depende de `posicoes_sptrans`)
4. `test_schedules_exist` — `defs.get_schedule_defs()` contém 4 schedules
5. `test_schedules_cron_valid` — todos os `cron_schedule` são expressões cron válidas
6. `test_jobs_exist` — `defs.get_job_defs()` contém 4 jobs
7. `test_asset_code_location` — validar que `workspace.yaml` aponta para `assets`

### Tarefa 4.2: Atualizar CI

- Adicionar `dagster` ao `pip install` no CI workflow
- CI continua rodando `pytest tests/ -v --tb=short`

### Verificação

```bash
pytest tests/test_assets.py -v
# → 7/7 passed
```

---

## Plano: Épico 5 — README Finalizar

### Tarefa 5.1: Verificar README atual

Já contém:
- [x] Badge CI no topo
- [x] Stack com Dagster
- [x] Diagrama Mermaid com subgraph Dagster
- [x] Estrutura do projeto com `assets/`
- [x] Seção "Orquestração (Dagster)" com tabela de assets + schedules
- [x] Instruções de docker compose e `dagster dev`

Pendente:
- [ ] Comando `make up` / `make down` referenciado (Makefile existe com targets test/lint)

### Tarefa 5.2: Verificar Makefile

Makefile atual tem: `install`, `install-dev`, `test`, `lint`, `clean`.
Adicionar `make up` e `make down`?

Decisão: **Não adicionar** por enquanto — Docker Compose já cobre com
`docker compose up/down`. Makefile para targets de desenvolvimento.

---

## Plano: Migração PostgreSQL (Estágio 2)

> **Status:** ⏳ Planejamento apenas — não executar sem aprovação

### Contexto

SQLite é adequado para o coletor (single-writer local), mas limita:

1. **Escrita concorrente:** SQLite locka em `INSERT` simultâneo
2. **Crescimento:** 97MB em ~2 semanas de dados; projeção: ~1.5GB/ano
3. **Sem rede:** não pode ser servido como fonte de verdade para múltiplos consumidores
4. **Sem roles/permissões:** qualquer processo com acesso ao arquivo pode modificar

### Abordagem Proposta

```
Coletores → PostgreSQL (OLTP, janela quente)
                    ↓ (Dagster: compactacao)
                Parquet (OLAP, DuckDB)
                    ↓
              Dashboard / Análise
```

### Trade-offs

| Opção | Prós | Contras |
|-------|------|---------|
| **SQLAlchemy + psycopg2** | ORM padrão, migração gradual | Overhead de ORM para schema simples (2 tabelas) |
| **asyncpg direto** | Máximo desempenho, async nativo | Precisa reescrever conexões dos coletores |
| **Manter SQLite + Parquet (status quo)** | Zero mudança, schema funciona | Próximo gargalo real é concorrência |

### Recomendação

**SQLAlchemy + psycopg2** — menor caminho de migração.

- `inicializar_banco.py` ganha flag `--db postgresql://...` (ou variável de ambiente `DATABASE_URL`)
- Coletores e assets usam `create_engine()` para abstrair SQLite/PostgreSQL
- Schema SQL mantido (CREATE TABLE compatível com PostgreSQL com ajustes menores)

### Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Perda de dados na migração | Baixa | Desligar coletores, dump SQLite → CSV, import para PostgreSQL |
| Schema incompatível (SQLite × PostgreSQL) | Média | `TEXT` vs `VARCHAR`, `INTEGER` vs `SERIAL` — mapear em `inicializar_banco.py` |
| Custo de manter PostgreSQL local | Baixa | Docker Compose com postgres:16-alpine (~200MB RAM) |
| Downtime durante migração | Alta (1x) | Planejar janela de manutenção, rollback via dump SQLite |

### Caminho de Migração (se aprovado)

```
Fase 1: docker-compose.yml + serviço postgres
Fase 2: src/inicializar_banco.py com suporte a DATABASE_URL
Fase 3: Coletores + assets usam engine configurável
Fase 4: Dump SQLite → PostgreSQL (one-shot)
Fase 5: Testes com PostgreSQL via fixture Docker
Fase 6: Remover SQLite como fonte de verdade (manter como fallback)
```

### Rollback

```bash
docker compose down -v postgres
git revert HEAD~N
# Coletores voltam a usar SQLite (engine padrão)
```

---

## STOP Conditions

### Épico 4 — Testes

- [ ] `pytest tests/test_assets.py -v` — 0 failures
- [ ] `ruff check tests/test_assets.py` — 0 violações
- [ ] `python -c "from assets import defs; print('OK')"` — carrega sem erro

### Épico 5 — README

- [ ] README contém badge CI, seção orquestração, stack, diagrama

### PostgreSQL (plano apenas)

- [ ] Plano revisado e aprovado por Roberto antes de qualquer execução

---

## Validação Final

| Critério | Status Esperado |
|----------|----------------|
| 7 testes de asset passando | ✅ |
| Ruff limpo | ✅ |
| README completo | ✅ |
| Plano PostgreSQL documentado | ✅ |

---

## Processing Context

### ◈ Processing Context

- ✦ **Lead Agent:** OpenCode Chief Engineer (DeepSeek V4 Flash)
- ▫ **Supporting Agents:** Nenhum subagente invocado — SINGLE com skills
- ⌥ **Skills Used:** `write-implementation-plan`, `goal-driven-execution`, `data-engineering`
- ☄ **Knowledge Sources:** `docs/plans/PRD_orquestracao.md`, `assets/*.py`, `docker-compose.yml`, `README.md`
- ☱ **Files Analyzed:** `assets/__init__.py`, `tests/`, `.github/workflows/ci.yml`, `docker-compose.yml`, `README.md`
- ◬ **Decision Complexity:** T3-LOW — planos independentes, sem interdependência
- 🤖 **Model Used:** DeepSeek V4 Flash (workhorse)
- 🔁 **Model Recommendation for Next Step:** Manter DeepSeek V4 Flash para Épico 4 (testes são mecânicos)
- 💰 **Budget Notes:** Plano leve (~30 min de leitura + ~15 min para testes)
