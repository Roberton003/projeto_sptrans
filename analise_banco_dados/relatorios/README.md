# Projeto SPTrans — Análise de Atrasos

Repositório com a análise de atrasos dos ônibus da SPTrans, cruzando dados internos com previsões do Moovit e gerando um dashboard interativo com Plotly.

## Estrutura sugerida

- `src/` – Código-fonte (scripts Python, notebooks)
- `data/` – Dados CSV (adicionar apenas amostras ou dados anonimizados)
- `reports/` – Relatórios gerados (txt, md, HTML)
- `assets/` – Arquivos estáticos (HTML finais, imagens, screenshots)
- `docs/` – Documentação e notas de implementação

## Como executar localmente

1. Crie um ambiente virtual (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Rode o script principal (gera `dashboard_atrasos_bi.html`):

```bash
python src/dashboard_atrasos.py
```

4. Abra `dashboard_atrasos_bi.html` no browser.

## Notas importantes

- Não comite dados sensíveis ou grandes volumes de CSV; inclua amostras em `data/` e documente o formato no `README`.
- Se pretende subir o repositório ao GitHub, crie um repositório público/privado e siga `git` normal (`git init`, `git add`, `git commit`, `git remote add origin ...`, `git push`).

## Próximos passos recomendados

- Adicionar `requirements.txt` (feito).
- Adicionar `LICENSE` e `CONTRIBUTING.md` se for colaborar.
- Transformar os exercícios em `notebooks/` para demonstração interativa.
- Criar um `Dockerfile` ou GitHub Action para gerar o dashboard automaticamente.

---

Arquivos principais presentes atualmente no diretório `relatorios/` foram parcialmente organizados para seguir esta estrutura.