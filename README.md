# Projeto SPTrans: Pipeline de Dados de Transporte Público

Este projeto implementa um pipeline de dados completo para coleta, processamento e visualização de dados em tempo real do transporte público de São Paulo, utilizando a API Olho Vivo da SPTrans.

A arquitetura é baseada em Docker, com serviços modularizados para garantir escalabilidade e facilidade de manutenção.

## Arquitetura e Serviços

*   **`coleta-posicoes`**: Serviço contínuo que captura dados de geolocalização dos ônibus.
*   **`coleta-previsoes`**: Serviço contínuo que captura previsões de chegada dos ônibus nas paradas.
*   **`dashboard`**: Serviço sob demanda que inicia um painel interativo em Streamlit para visualização dos dados.
*   **`notebook`**: Serviço sob demanda que inicia um ambiente Jupyter Lab para análises exploratórias.
*   **`analise`**: Serviço sob demanda para executar scripts de análise específicos.

## Tecnologias Utilizadas

*   **Linguagem:** Python 3.11
*   **Pipeline e Orquestração:** Docker, Docker Compose
*   **Bibliotecas Principais:** `requests`, `pandas`, `streamlit`
*   **Controle de Versão:** Git, GitHub

## Estrutura do Projeto

A estrutura foi reorganizada para isolar o código-fonte da aplicação:

```
.
├── src/                     # Contém todo o código-fonte da aplicação
│   ├── coleta_sptrans.py
│   ├── coleta_previsoes.py
│   ├── dashboard_sptrans.py
│   └── utils/
├── arquivos_arquivados/     # Scripts antigos e artefatos não essenciais
├── docker-compose.yml       # Orquestração dos serviços
├── Dockerfile               # Definição do ambiente da aplicação
├── run_all.sh               # Script para INICIAR os coletores
├── stop_all.sh              # Script para PARAR os coletores
└── README.md
```

## Como Rodar o Projeto

### Pré-requisitos

*   Docker e Docker Compose instalados.
*   Uma chave de acesso (token) da API Olho Vivo da SPTrans.

### Configuração

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Roberton003/projeto_sptrans.git
    cd projeto_sptrans
    ```
2.  **Configure a API Key:**
    *   Crie o arquivo de configuração: `cp config/config.ini.template config/config.ini`
    *   Edite o arquivo `config/config.ini` e insira sua chave da API.

### Execução

O gerenciamento dos serviços é feito de forma simples através dos scripts `run_all.sh` e `stop_all.sh`.

1.  **Iniciar os Coletores de Dados:**
    Este comando irá construir as imagens Docker (se for a primeira vez) e iniciar os serviços `coleta-posicoes` e `coleta-previsoes` em background.
    ```bash
    ./run_all.sh
    ```

2.  **Parar os Coletores de Dados:**
    Este comando para e remove todos os contêineres da aplicação.
    ```bash
    ./stop_all.sh
    ```

## Como Usar os Serviços Adicionais

Para usar o dashboard ou o ambiente de análise, execute os seguintes comandos em um novo terminal:

*   **Para iniciar o Dashboard:**
    ```bash
    docker-compose run --rm -p 8501:8501 dashboard
    ```
    Acesse o dashboard em: `http://localhost:8501`

*   **Para iniciar o Jupyter Lab:**
    ```bash
    docker-compose run --rm -p 8888:8888 notebook
    ```
    Acesse o Jupyter em: `http://localhost:8888`

## 📚 Documentação Interna

Para informações sobre planejamento, roadmap e melhorias do projeto, consulte a pasta `.docs_internos/`:

- **Comece aqui:** `.docs_internos/GUIA_RAPIDO_COMECE_AQUI.md`
- **Roadmap completo:** `.docs_internos/PRD_MELHORIAS_FASE2.md`
- **Índice de documentos:** `.docs_internos/INDICE_DOCUMENTOS.md`

> ℹ️ **Nota:** A pasta `.docs_internos/` é ignorada no repositório (não aparece no GitHub). É destinada a planejamento e desenvolvimento interno.

## Contribuição

Sinta-se à vontade para contribuir! Por favor, consulte o arquivo `CONTRIBUTING.md` para mais detalhes.