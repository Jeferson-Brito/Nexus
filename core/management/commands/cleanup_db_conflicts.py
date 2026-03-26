from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Resolve conflitos de migração de forma inteligente (idempotente)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- INICIANDO SINCRONIZAÇÃO INTELIGENTE ---'))
        
        with connection.cursor() as cursor:
            # Função auxiliar para checar coluna
            def column_exists(table, column):
                cursor.execute("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name=%s AND column_name=%s
                """, [table, column])
                return cursor.fetchone() is not None

            # Função auxiliar para fakar migração
            def fake_migration(app, name):
                cursor.execute("SELECT 1 FROM django_migrations WHERE app=%s AND name=%s", [app, name])
                if not cursor.fetchone():
                    self.stdout.write(f'Fakando migração: {name}')
                    cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now())", [app, name])

            # 1. Resolver conflito da 0072 (fluxo_aprovacao)
            if column_exists('core_department', 'fluxo_aprovacao'):
                self.stdout.write('Coluna fluxo_aprovacao já existe em core_department.')
                fake_migration('core', '0072_department_fluxo_aprovacao')

            # 2. Resolver conflito da 0073 (show_in_nav)
            if column_exists('core_department', 'show_in_nav'):
                self.stdout.write('Coluna show_in_nav já existe em core_department.')
                fake_migration('core', '0073_department_show_in_nav')

            # 3. Limpeza de índices (caso ainda existam)
            self.stdout.write('Limpando índices residuais...')
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555 CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555_like CASCADE;")

        self.stdout.write(self.style.SUCCESS('--- SINCRONIZAÇÃO CONCLUÍDA ---'))
