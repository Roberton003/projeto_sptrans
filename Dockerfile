# Etapa 1: Imagem Base
# Começamos com uma imagem oficial do Python. A tag 'slim' é uma versão leve, ótima para produção.
FROM python:3.11-slim

# Boas práticas: garante que os logs do Python apareçam em tempo real nos logs do Docker
ENV PYTHONUNBUFFERED=1

# Etapa 2: Configurar o Ambiente de Trabalho
# Criamos uma pasta dentro do container para o nosso projeto.
WORKDIR /app

# Etapa 3: Instalar as Dependências
# Copiamos apenas o requirements.txt primeiro. O Docker é inteligente e, se este arquivo não mudar,
# ele reutiliza o cache desta camada, tornando builds futuros muito mais rápidos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 4: Copiar o Código da Aplicação
# Agora, copiamos todo o resto do nosso projeto para dentro da pasta /app no container.
COPY . .

# (Não definimos um CMD ou ENTRYPOINT aqui, pois vamos controlar qual script rodar através do Docker Compose)
