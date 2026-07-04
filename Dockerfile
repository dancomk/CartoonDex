# 1. Usa uma imagem oficial do Python estável e leve
FROM python:3.11-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Evita que o Python escreva arquivos .pyc e garante que os logs apareçam na hora
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. CORREÇÃO DO ERRO: Garante que a variável do Nixpacks não quebre se for chamada
ENV NIXPACKS_PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 5. Instala dependências do sistema que o Pillow (biblioteca de imagem) pode precisar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /lib/apt/lists/*

# 6. Copia primeiro apenas o arquivo de dependências (evita reinstalar tudo a cada alteração de código)
COPY requirements.txt .

# 7. Instala as dependências do seu bot
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copia todo o restante dos arquivos do seu projeto para dentro do container
COPY . .

# 9. Comando que inicia o seu bot (ajuste se o seu arquivo principal tiver outro nome)
CMD ["python", "bot.py"]