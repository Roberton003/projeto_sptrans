# Projeto SPTrans

Este projeto coleta, analisa e visualiza dados do transporte público de São Paulo, utilizando a API da SPTrans.

## Automação

Para automatizar o processo de commit e push para o GitHub, utilize o script `github_automation.py`.

**Uso:**

```bash
python3 scripts/github_automation.py
```

O script irá:

1.  Verificar o status do Git e inicializar um novo repositório se necessário.
2.  Sugerir o nome do repositório com base no nome da pasta do projeto.
3.  Perguntar se o repositório deve ser privado.
4.  Criar o repositório no GitHub (se ainda não existir).
5.  Adicionar todos os arquivos modificados ao stage.
6.  Solicitar uma mensagem de commit.
7.  Fazer o push para o branch especificado (o padrão é `main`).