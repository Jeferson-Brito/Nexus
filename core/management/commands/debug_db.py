from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

class Command(BaseCommand):
    help = 'Displays the current state of the database (tables and migrations)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- DIAGNÓSTICO DO BANCO DE DADOS ---'))
        
        # 1. Listar Tabelas
        self.stdout.write('Tabelas existentes no schema public:')
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            tables = cursor.fetchall()
            for table in tables:
                self.stdout.write(f"  - {table[0]}")
        
        # 2. Listar Migrações Aplicadas
        self.stdout.write('\nMigrações registradas no Django:')
        try:
            recorder = MigrationRecorder(connection)
            applied = recorder.applied_migrations()
            for (app, name) in sorted(applied.keys()):
                self.stdout.write(f"  - {app}: {name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao ler migrações: {e}"))

        # 3. Verificar o índice específico do erro anterior
        self.stdout.write('\nVerificando índices específicos:')
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT relname as indexname
                FROM pg_class
                WHERE relname = 'core_storeauditissue_status_f5972555';
            """)
            indexes = cursor.fetchall()
            if indexes:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Índice encontrado: {indexes[0][0]}"))
            else:
                self.stdout.write("  ✅ Índice 'core_storeauditissue_status_f5972555' não encontrado.")

        self.stdout.write(self.style.SUCCESS('\n--- FIM DO DIAGNÓSTICO ---'))
