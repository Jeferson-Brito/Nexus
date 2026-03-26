#!/bin/bash

# Sair se houver erro
set -e

echo "==> Iniciando inicialização do sistema..."

# 1. Executar migrações (Primeiro passo crítico)
python manage.py migrate --noinput

# 2. Coletar arquivos estáticos
python manage.py collectstatic --noinput --no-post-process

# 3. Auto-healing do esquema do banco (Corrigir colunas de migrações anteriores)
python manage.py ensure_schema

# 4. Corrigir permissões e IDs duplicados + Seeding de Departamentos
python manage.py fix_permissions

# 5. Inicializar dados de produção (admin)
python manage.py init_production

echo "==> Sistema inicializado. Iniciando Gunicorn..."

# Iniciar o servidor de aplicação
exec gunicorn nexus.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 100
