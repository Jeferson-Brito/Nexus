import os
os.environ['DB_NAME'] = 'nexus_staging'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
import django
django.setup()
from django.core.management import call_command

print("Rodando migrations no nexus_staging...")
call_command('migrate')
print("Migração concluída.")
