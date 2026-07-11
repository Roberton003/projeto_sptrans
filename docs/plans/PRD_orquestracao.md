# PRD — Orquestração Profissional do Pipeline SPTrans

> **Estágio:** 1/4 (Roadmap: Orquestração → PostgreSQL → Data Lake → Cloud)
> **Contexto:** Pipeline funciona com `schedule` + cron local + Docker
> **Objetivo:** Substituir agendamento embutido por orquestrador profissional
>   com DAGs, retry, SLA, alertas e observabilidade.

---

## Problema Real

O pipeline atual coleta ~555k posições/dia, mas o agendamento é frágil:

1. **`schedule` library** dentro do código — sem visibilidade de falha, sem retry
2. **Docker `restart: unless-stopped`** — único mecanismo de resiliência
3. **Zero observabilidade** — não há métricas de sucesso/falha por execução
4. **Sem lineage** — sem rastreamento de qual execução produziu quais dados
5. **Escalar para 3+ tarefas** (coleta→compactação→expurgo→dashboard) já
   exigiria coordenação manual

**Evidência:** `requirements.txt` contém `schedule` — agendamento dentro do
processo Python, sem separação entre lógica de negócio e orquestração.

---

## Escopo

### Incluído

- Orquestrador (Airflow ou Dagster) em Docker Compose
- DAGs/Assets para: `coleta_sptrans`, `coleta_previsoes`, `compactar_parquet`,
  `expurgar_sqlite`
- Retry configurado por tarefa
- Logs centralizados + métricas de sucesso/falha
- Testes de DAG/Asset (validação de parsing, schedule, dependências)
- README atualizado com instruções de orquestração
- Makefile com target `up` / `down` para o stack completo

### Fora de Escopo

- **Streaming (Kafka):** injustificado — API Olho Vivo é REST polling
- **PostgreSQL:** será o Estágio 2; SQLite continua como fonte de verdade
- **dbt/transformações:** será o Estágio 3
- **Cloud/Deploy:** Estágio 4
- **Novas análises ou dashboards**
- **Mudança no schema das tabelas**

---

## Decisão: Airflow vs Dagster

| Critério | Airflow | Dagster |
|----------|---------|---------|
| Curva de aprendizado | Alta (config + plugins + providers) | Média (Python-first) |
| Modelo mental | DAG de tarefas operacionais | Assets de dados (mapeia naturalmente para tabelas/parquets) |
| Integração com DuckDB/Parquet | Provider community | Nativo via `PandasIOManager` / custom I/O |
| Testabilidade | `dagster-pytest` nativo | `dagster-test` (melhor) |
| Adoção no mercado | **Mais requisitado** em vagas | Crescendo rápido, moderno |
| Skill disponível no harness | Não | ✅ `dagster-expert` |
| Complexidade operacional | 3+ containers (scheduler, worker, webserver, DB) | 2 containers (daemon + webserver) |
| DRY com nosso modelo de dados | Schema como string SQL | Assets tipados com `@asset` décorator |

### Veredito

**Recomendo Dagster** para este projeto. Razões:

1. **Modelo de assets** mapeia 1:1 com nossas tabelas e Parquet — cada asset
   (`posicoes`, `previsoes`, `parquet_posicoes`) é um nó com dependência
   explícita, sem precisar de `DummyOperator` ou `BranchPythonOperator`.
2. **I/O Managers** permitem ler/escrever SQLite, DuckDB e Parquet sem
   boilerplate de conexão dentro da DAG.
3. **Testabilidade nativa** — `dagster dev` com reload automático.
4. **Skill `dagster-expert`** disponível no harness para implementação guiada.
5. **Curva menor** para um projeto de 4 tasks — Airflow exige configuração
   desproporcional (CeleryExecutor, banco de resultados, etc.).

> Se o objetivo for **maximizar empregabilidade em vagas tradicionais**,
> Airflow é o padrão ouro e a decisão seria diferente. Se o objetivo for
> **demonstrar engenharia moderna de dados** com a stack mais coerente para
> o projeto, Dagster é superior neste caso específico.

---

## Épicos

### Épico 1 — Setup do Orquestrador

- Adicionar serviço Dagster (daemon + webserver + code location) no
  `docker-compose.yml`
- `dagster.yaml` com configuração de retry, log, storage (filesystem local)
- `workspace.yaml` apontando para o diretório de assets
- Script de entrada que instala dependências (`pip install dagster dagster-webserver`)
- Makefile com `make up` (docker compose up) e `make down`

**Verificação:** `docker compose up` → webserver em `localhost:3000`

### Épico 2 — Assets de Coleta

- `assets/coleta.py`: `@asset` para `posicoes` (chama `coleta_sptrans.job()`)
- `assets/previsoes.py`: `@asset` para `previsoes` (chama `coleta_previsoes.job()`)
- Configurar `IOManager` para SQLite
- Retry: 3 tentativas com backoff de 60s
- Schedule: `@schedule` ou `@sensor` com polling a cada 5 min (posições) e
  15 min (previsões)

**Verificação:** `dagster dev` → materializar assets no UI

### Épico 3 — Assets de Processamento

- `assets/compactacao.py`: `@asset` dependente de `posicoes` e `previsoes`,
  chama `compactar_parquet.exportar_tabela()` para cada tabela
- `assets/expurgo.py`: `@asset` dependente de `posicoes` e `previsoes`,
  chama `expurgar_sqlite.expurgar()` com janela de 7 dias
- Schedule diário para ambos

**Verificação:** materializar asset de compactação → Parquet atualizado

### Épico 4 — Testes de Orquestração

- `tests/test_assets.py`: validar que os assets são carregados sem erro de
  parsing, dependências estão corretas, schedules têm `cron_schedule` válido
- `tests/test_job_config.py`: validar que a configuração de resources
  (db_path, parquet_dir) está correta
- CI atualizado para rodar testes com `dagster`

**Verificação:** `pytest tests/ -q` — 0 failures

### Épico 5 — README + Docs

- Seção de orquestração no README com diagrama atualizado
- Instruções de `dagster dev` para desenvolvimento local
- Documentar schedules (o quê, quando, SLA esperado)

**Verificação:** README revisado

---

## Estrutura Alvo

```
.
├── assets/                  # NOVO: Assets Dagster
│   ├── __init__.py          # Definitions (assets + schedules + resources)
│   ├── coleta.py            # posicoes, previsoes
│   ├── processamento.py     # compactacao, expurgo
│   └── io_managers.py       # SQLiteIOManager custom
├── src/                     # Inalterado (scripts chamados pelos assets)
├── tests/
│   └── test_assets.py       # NOVO
├── docker-compose.yml       # Atualizado (+ dagster-webserver, dagster-daemon)
├── dagster.yaml             # NOVO
└── workspace.yaml           # NOVO
```

---

## Dependências

| Library | Motivo |
|---------|--------|
| `dagster` | Orquestrador |
| `dagster-webserver` | UI do Dagster |
| `dagit` | (alias, instalado com webserver) |

Todas são pip install — sem containers extras além do Docker Compose.

---

## Rollout

```
1. docker-compose.yml com serviços Dagster (code location + webserver + daemon)
2. assets básicos (coleta) — schedule 5/15 min
3. assets de processamento (compactação + expurgo) — schedule diário
4. testes de asset + CI
5. docs + handoff
```

## Rollback

```
1. `git revert` dos commits de assets e docker-compose
2. `docker compose down -v` para limpar volumes do Dagster
3. Coletores voltam a rodar via `schedule` (código src/ inalterado)
```

---

## Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Dagster daemon consome CPU ocioso | Média | Container com `--memory` limit no compose |
| SQLite lock com assets concorrentes | Alta | Assets serializados por `@asset(execution=OP`) |
| `schedule` removido antes de orquestrador estável | Baixa | Manter schedule como fallback até Épico 5 |
| Dagster version muda API | Baixa | Pino `dagster==1.12.x` no requirements |

---

## Processamento

### ◈ Processing Context

- ✦ **Lead Agent:** OpenCode Chief Engineer (DeepSeek V4 Flash)
- ▫ **Supporting Agents:** Nenhum subagente invocado — este é apenas um PRD
- ⌥ **Skills Used:** `write-implementation-plan`, `goal-driven-execution`, `data-engineering`
- ☄ **Knowledge Sources:** `docs/plans/PRD_profissionalizacao.md`, `src/*.py`,
  `docker-compose.yml`, `requirements.txt`
- ☱ **Files Analyzed:** `src/inicializar_banco.py`, `requirements.txt`, `docker-compose.yml`,
  `docs/plans/PRD_profissionalizacao.md`, `docs/plans/RELATORIO_EXECUCAO.md`
- ◬ **Decision Complexity:** T3-LOW — pipeline conhecido, assets mapeáveis 1:1
- 🤖 **Model Used:** DeepSeek V4 Flash (workhorse)
- 🔁 **Model Recommendation for Next Step:** Carregar `dagster-expert` skill
  para implementação detalhada dos assets
- 💰 **Budget Notes:** PRD leve (~5 mins de leitura). Implementação: 4-5 épocos,
  estimativa T3-LOW
