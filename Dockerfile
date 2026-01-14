FROM python:3.12-slim

# Evita buffers no stdout (logs em tempo real)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Dependências do sistema (psycopg2, pillow, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o projeto
COPY . .

# Porta usada pelo Gunicorn
EXPOSE 8000

# Comando padrão (pode ser sobrescrito pelo compose)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "main:app"]

