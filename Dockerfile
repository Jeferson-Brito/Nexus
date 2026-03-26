# Usar a imagem oficial do Python, versão slim para otimização
FROM python:3.11-slim

# Variáveis de ambiente para o Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Diretório de trabalho no container
WORKDIR /app

# Instalar dependências do sistema para o psycopg e outras libs
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código do projeto para o container
COPY . /app/

# Tornar o script de inicialização executável
RUN chmod +x /app/start.sh

# Porta que o Django expõe (Render cuidará do binding)
EXPOSE 8000

# Script de entrada
CMD ["/app/start.sh"]
