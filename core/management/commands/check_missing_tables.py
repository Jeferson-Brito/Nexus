from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Verifica se as tabelas principais do app core existem'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- VERIFICANDO TABELAS ---'))
        
        tables_to_check = [
            'core_user',
            'core_department',
            'core_conversation',
            'core_conversation_participants',
            'core_message',
            'core_useronlinestatus',
            'core_colaborador',
            'core_venda',
        ]
        
        with connection.cursor() as cursor:
            for table in tables_to_check:
                cursor.execute("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema='public' AND table_name=%s
                """, [table])
                exists = cursor.fetchone() is not None
                status = "OK" if exists else "FALTANDO"
                self.stdout.write(f"Tabela {table.ljust(30)}: {status}")
        
        self.stdout.write(self.style.SUCCESS('--- FIM DA VERIFICAÇÃO ---'))
