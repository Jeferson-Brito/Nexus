from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Remove conflitos conhecidos do banco de dados antes das migrações'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- INICIANDO LIMPEZA DE CONFLITOS ---'))
        
        with connection.cursor() as cursor:
            # 1. Dropar o índice problemático da storeauditissue
            # Se ele já existe e a migração tenta criar, o Django falha.
            # Ao dropar aqui, a migração poderá criá-lo do jeito certo.
            self.stdout.write('Dropando índices de core_storeauditissue...')
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555 CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555_like CASCADE;")
            
            # 2. Outros possíveis conflitos da migração 0065
            self.stdout.write('Dropando outros índices da 0065 (por segurança)...')
            cursor.execute("DROP INDEX IF EXISTS core_storeaudit_created_at_4d77e40e CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeaudit_created_at_4d77e40e_like CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_created_at_32f9a3e8 CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_created_at_32f9a3e8_like CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_analystassignment_active_7f972555 CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_analystassignment_active_7f972555_like CASCADE;")

        self.stdout.write(self.style.SUCCESS('--- CONFLITOS REMOVIDOS ---'))
