# PRD — Profissionalização do projeto_sptrans (higiene + fundamentos)

> **Constitution:** Phase Gates dos Artigos III, IV, VI, VII da Spec Constitution do harness opencode.
> **Origem:** Plano de carreira Roberto (Claude Code, 08/07/2026). Prioridade 4 de 4.
> **Executor:** opencode + agentes. **Revisor:** Claude Code por épico.

---

## Contexto

Auditoria (08/07/2026): pipeline real-time com boa base operacional (Docker Compose com coletores contínuos `restart: unless-stopped`, .gitignore rigoroso, pre-commit black/isort), mas fundamentos de engenharia ausentes:

- **1 único teste** (`tests/test_main.py`); **sem CI** (`.github/workflows/` inexistente).
- **Sem idempotência**: coletores (`coleta_sptrans.py`, `coleta_previsoes.py`) fazem append em SQLite sem chave de dedup — re-runs/reconexões duplicam linhas.
- **Sem camada de transformação**: análise é pandas ad-hoc em `analise_onibus.py`; acúmulo cresce indefinidamente em SQLite (97MB em `data/` local).
- `arquivos_arquivados/` com código morto/legado dobra a superfície aparente do repo; logs (`coleta.log`, `coleta_previsoes.log` 459K) na raiz.
- `scripts/github_automation.py` (automação de auto-promoção) não pertence ao pipeline.

## Objetivo

Pipeline com dedup provada, camada analítica Parquet/DuckDB (evolução de maturidade visível), testes reais e CI. Critério de sucesso: Critérios de Aceite finais.

## Escopo

### Incluído
Épicos 1–5.

### Fora de Escopo
- Migrar SQLite → Postgres (SQLite é adequado ao coletor local; a evolução analítica vai para Parquet/DuckDB, não para outro OLTP).
- Kafka/streaming real (polling da API Olho Vivo é o padrão da fonte).
- Novas análises/dashboards além da adaptação ao DuckDB.

---

## Épicos (ordem de execução)

### Épico 1 — Higiene (bloqueante)
1. Deletar `arquivos_arquivados/` do disco e garantir fora do git (já gitignorado — confirmar `git ls-files`).
2. Remover logs da raiz (`coleta.log`, `coleta_previsoes.log`); logging vai para `data/logs/` (gitignorado) ou stdout (padrão container — preferido, já que roda em compose).
3. Mover `scripts/github_automation.py` para fora do repo (ou `.private/` gitignorado).
4. Limpar `.ipynb_checkpoints/`, garantir dupla venv (`venv/` e `.venv/`) fora do git.

### Épico 2 — Dedup / Idempotência
1. Definir chave natural por tabela: posições = (id_veiculo, timestamp_captura); previsões = (id_veiculo, parada, horario_previsto, timestamp_captura) — validar contra o schema real em `inicializar_banco.py`.
2. `CREATE UNIQUE INDEX` nas chaves + `INSERT OR IGNORE` nos coletores.
3. Migração dos dados existentes: script one-shot que deduplica a base atual antes de criar o índice.
4. Teste: inserir o mesmo payload 2× → contagem idêntica.

### Épico 3 — Camada analítica Parquet + DuckDB
1. `src/compactar_parquet.py`: exporta SQLite → Parquet particionado por data (`data/parquet/posicoes/dt=YYYY-MM-DD/`), idempotente por partição (overwrite determinístico da partição do dia).
2. Serviço opcional no compose (`compactacao`, roda 1×/dia) ou target no Makefile.
3. Dashboard (`dashboard_sptrans.py`) e `analise_onibus.py` passam a consultar via DuckDB sobre os Parquet (com fallback SQLite para dados do dia corrente) — mostra a evolução SQLite→lakehouse local.
4. Documentar retenção: SQLite guarda janela quente (ex.: 7 dias), Parquet é o histórico. Script de expurgo da janela.

### Épico 4 — Testes + CI
1. `tests/`: coleta com mock da API Olho Vivo (auth + posições), dedup (Épico 2.4), compactação Parquet (fixture pequena), smoke do dashboard (import + função de query).
2. `.github/workflows/ci.yml`: ruff + pytest. Adicionar ruff ao pre-commit (substituindo ou somando a black/isort — preferir ruff format+lint, menos ferramentas).
3. Badge CI no README.

### Épico 5 — README honesto com diagrama
1. Diagrama (Mermaid): API Olho Vivo → coletores (compose) → SQLite (janela quente) → Parquet particionado → DuckDB → Streamlit.
2. Seção "Limitações e decisões": polling (não streaming), SQLite local, retenção — limites declarados explicitamente.
3. Instruções de setup verificadas em máquina limpa (`docker compose up`).

---

## Phase Gates

### Simplicity Gate (Art. VI)
- [x] Cada estágio uma responsabilidade: coleta / dedup no insert / compactação / consulta.
- [x] SQLite→Parquet→DuckDB é medallion informal (quente/frio/analítico); documentado no README.
- [x] Nenhum god transform — compactação só move/particiona.

### Intentional Abstraction Gate (Art. VII)
- [x] Zero abstração nova; scripts diretos com stdlib + duckdb/pyarrow.
- [x] Raw acessível: SQLite (quente) e Parquet (histórico) auditáveis.

### Data Contract Gate (Art. III)
- [ ] Épico 2.1 documenta schema + chaves naturais por tabela (em `docs/data-contract.md`).
- [ ] Freshness: coletores contínuos; documentar intervalo esperado e como verificar atraso.
- [x] Volume: retenção definida no Épico 3.4.

### Idempotency Gate (Art. IV)
- [ ] Insert idempotente (Épico 2) + compactação idempotente por partição (Épico 3.1) + testes 2×.

## Complexity Tracking

| Gate | Status | Justificativa |
|------|--------|---------------|
| Simplicity (Art. VI) | ✅ Aprovado | Épico 1 remove código morto; novos scripts mínimos |
| Intentional Abstraction (Art. VII) | ✅ Aprovado | Sem abstrações |
| Data Contract (Art. III) | ✅ Aprovado | Entrega dos Épicos 2–3 |
| Idempotency (Art. IV) | ✅ Aprovado | Núcleo dos Épicos 2–3 |

## Critérios de Aceite

- [ ] Payload idêntico inserido 2× → contagem idêntica (teste automatizado).
- [ ] Compactação re-executada sobre a mesma partição → Parquet idêntico (hash).
- [ ] Dashboard consulta DuckDB sobre Parquet e responde.
- [ ] CI verde (ruff + pytest) no GitHub Actions.
- [ ] `arquivos_arquivados/`, logs de raiz e `github_automation.py` fora do repo.
- [ ] README com diagrama Mermaid e seção de limitações; setup funciona em clone limpo via compose.
