from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Garante que colunas críticas existam no banco de dados (Self-healing)"

    def handle(self, *args, **options):
        self.stdout.write("Verificando consistência do esquema do banco de dados...")
        
        with connection.cursor() as cursor:
            # 1. Verificar core_department.fluxo_aprovacao
            if not self.column_exists(cursor, "core_department", "fluxo_aprovacao"):
                self.stdout.write(self.style.WARNING("Coluna 'fluxo_aprovacao' ausente em 'core_department'. Adicionando..."))
                cursor.execute('ALTER TABLE core_department ADD COLUMN fluxo_aprovacao VARCHAR(100) DEFAULT \'\'')
                self.stdout.write(self.style.SUCCESS("✓ Coluna 'fluxo_aprovacao' adicionada."))

            # 2. Verificar core_department.show_in_nav
            if not self.column_exists(cursor, "core_department", "show_in_nav"):
                self.stdout.write(self.style.WARNING("Coluna 'show_in_nav' ausente em 'core_department'. Adicionando..."))
                cursor.execute('ALTER TABLE core_department ADD COLUMN show_in_nav BOOLEAN DEFAULT FALSE')
                self.stdout.write(self.style.SUCCESS("✓ Coluna 'show_in_nav' adicionada."))

            # 3. Adicionar mais verificações se necessário futuramente
            
        self.stdout.write(self.style.SUCCESS("Verificação de esquema concluída."))

    def column_exists(self, cursor, table_name, column_name):
        cursor.execute("""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, [table_name, column_name])
        return cursor.fetchone()[0] > 0
