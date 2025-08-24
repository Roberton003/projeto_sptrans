# Projeto SPTrans: Análise e Visualização de Dados de Transporte Público

Este projeto é uma solução completa para coleta, processamento, análise e visualização de dados do transporte público de São Paulo (SPTrans). Utilizando a API Olho Vivo da SPTrans, o sistema coleta informações em tempo real sobre a localização dos ônibus, permitindo análises aprofundadas e a criação de dashboards interativos para insights sobre a mobilidade urbana.

## Funcionalidades Principais

*   **Coleta de Dados:** Scripts Python para aquisição contínua de dados da API Olho Vivo da SPTrans (posições de ônibus, previsões de chegada).
*   **Armazenamento Eficiente:** Utilização de banco de dados SQLite para persistência dos dados coletados.
*   **Análise de Dados:** Módulos de análise para processar e extrair informações valiosas, como padrões de rota, tempos de viagem e desempenho das linhas.
*   **Visualização Interativa:** Dashboards desenvolvidos para apresentar os dados de forma clara e interativa, facilitando a compreensão e a tomada de decisões.
*   **Automação:** Processos automatizados para coleta, análise e atualização dos dashboards.
*   **Containerização:** Suporte a Docker e Docker Compose para fácil configuração e execução em diferentes ambientes.

## Tecnologias Utilizadas

*   **Linguagem:** Python 3.x
*   **APIs:** SPTrans Olho Vivo API
*   **Banco de Dados:** SQLite
*   **Bibliotecas Python:** `requests`, `pandas`, `matplotlib`, `dash` (ou similar para dashboards), `subprocess`, `os`, `json` (e outras conforme `requirements.txt`).
*   **Containerização:** Docker, Docker Compose
*   **Automação:** Shell Script, Make
*   **Controle de Versão:** Git, GitHub

## Estrutura do Projeto

```
.
├───.dockerignore
├───.gitignore
├───.pre-commit-config.yaml
├───analise_completa.py
├───analise_onibus.py
├───analise_v2.py
├───coleta_previsoes.py
├───coleta_sptrans.py
├───CONTRIBUTING.md
├───dashboard_sptrans.py
├───docker-compose.yml
├───Dockerfile
├───inicializar_banco.py
├───LICENSE
├───main.py
├───Makefile
├───monitor.py
├───painel_interativo_sp.py
├───pyproject.toml
├───README.md
├───requirements_dashboard.txt
├───requirements-dev.txt
├───requirements.txt
├───run_all.sh
├───stop_all.sh
├───arquivos_extras/
│   ├───Documentacao API _ SPTrans.pdf
│   ├───estrutura_projeto.md
│   ├───gerar_paineis.sh
│   ├───gerar_painel_interativo.sh
│   ├───gerar_painel.sh
│   ├───guia_api_olho_vivo_sptrans.pdf
│   ├───guia_api_olho_vivo_sptrans.py
│   └───Made with insMind-roberto2025.jpeg (e outras imagens)
├───config/
│   ├───config.ini
│   └───config.ini.template
├───data/
│   ├───analise_onibus.csv
│   ├───consulta_sql_csv_sptrans.py
│   ├───sptrans_data.db
│   └───todas_as_linhas.csv
├───notebooks/
│   ├───analise_exploratoria.ipynb
│   └───sptrans_coleta_analise.ipynb
├───scripts/
│   └───github_automation.py
├───tests/
│   ├───__init__.py
│   └───test_main.py
└───utils/
    ├───__init__.py
    └───utils.py
```

## Como Configurar e Rodar o Projeto

### Pré-requisitos

*   Python 3.x
*   Docker e Docker Compose (opcional, para execução containerizada)
*   Uma chave de acesso (token) da API Olho Vivo da SPTrans. Você pode obter uma em [link para o site da SPTrans API, se houver].

### Configuração

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/Roberton003/projeto_sptrans.git
    cd projeto_sptrans
    ```
2.  **Configurar a API Key:**
    Crie um arquivo `config/config.ini` a partir do template:
    ```bash
    cp config/config.ini.template config/config.ini
    ```
    Edite `config/config.ini` e insira sua chave da API da SPTrans.

3.  **Instalar Dependências:**
    É altamente recomendado usar um ambiente virtual:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements_dashboard.txt # Se for rodar o dashboard
    pip install -r requirements-dev.txt # Para desenvolvimento e testes
    ```

### Execução

#### Modo Local

*   **Inicializar o Banco de Dados:**
    ```bash
    python3 inicializar_banco.py
    ```
*   **Coletar Dados:**
    ```bash
    python3 coleta_sptrans.py
    python3 coleta_previsoes.py
    ```
*   **Rodar Análises:**
    ```bash
    python3 analise_completa.py
    # Ou execute os notebooks Jupyter
    jupyter lab
    ```
*   **Iniciar Dashboard:**
    ```bash
    python3 dashboard_sptrans.py
    # Ou
    python3 painel_interativo_sp.py
    ```
*   **Executar o Pipeline Completo (se `main.py` or `run_all.sh` or `Makefile` or `monitor.py` or `inicializar_banco.py` or `coleta_previsoes.py` or `coleta_sptrans.py` or `analise_completa.py` or `analise_onibus.py` or `analise_v2.py` or `dashboard_sptrans.py` or `painel_interativo_sp.py` or `consulta_sql_csv_sptrans.py` or `guia_api_olho_vivo_sptrans.py` is the entry point):**
    ```bash
    # Verifique o Makefile ou run_all.sh para o comando principal
    make all # Exemplo, se houver um target 'all'
    # Ou
    ./run_all.sh
    # Ou
    python3 main.py # Se for o ponto de entrada principal
    ```

#### Modo Containerizado (Docker)

1.  **Construir as imagens Docker:**
    ```bash
    docker-compose build
    ```
2.  **Iniciar os serviços:**
    ```bash
    docker-compose up -d
    ```
3.  **Parar os serviços:**
    ```bash
    docker-compose down
    ```

## Desafios e Soluções

Durante o desenvolvimento e a configuração inicial deste projeto, enfrentamos alguns desafios comuns que foram superados com sucesso, garantindo a robustez e a funcionalidade da aplicação:

1.  **Problemas de Caminho e Execução de Scripts:**
    *   **Desafio:** Erros como `python: can't open file ... [Errno 2] No such file or directory` indicavam que os scripts não estavam sendo encontrados ou executados do diretório correto.
    *   **Solução:** Padronizamos a execução dos scripts a partir do diretório raiz do projeto e fornecemos instruções claras sobre como navegar e executar os comandos.

2.  **Autenticação na API SPTrans:**
    *   **Desafio:** A API da SPTrans retornava `Authorization has been denied for this request.` após a primeira requisição, indicando que a sessão de autenticação não estava sendo mantida.
    *   **Solução:** Implementamos o uso de uma sessão `requests` persistente, que mantém o cookie de autenticação, garantindo que todas as requisições subsequentes sejam autenticadas corretamente.

3.  **Gerenciamento de Ambiente Virtual e Dependências:**
    *   **Desafio:** Dificuldades na criação e ativação do ambiente virtual, bem como na instalação das dependências necessárias (`venv/bin/activate: Arquivo ou diretório inexistente`, `pip install requests`).
    *   **Solução:** Fornecemos instruções detalhadas para a criação (`python3 -m venv venv`), ativação (`source venv/bin/activate`) e instalação de todas as dependências via `pip install -r requirements.txt`, garantindo um ambiente de desenvolvimento consistente.

Essas etapas foram cruciais para estabelecer uma base sólida para o projeto, permitindo a coleta e análise de dados de forma eficiente e confiável.

## Contribuição

Sinta-se à vontade para contribuir com este projeto! Por favor, consulte o arquivo `CONTRIBUTING.md` para mais detalhes sobre como começar.

## Licença

Este projeto está licenciado sob a [Nome da Licença, ex: Licença MIT]. Veja o arquivo `LICENSE` para mais detalhes.
