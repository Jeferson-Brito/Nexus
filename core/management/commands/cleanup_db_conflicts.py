from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Resolve conflitos de migração de forma inteligente (idempotente)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- INICIANDO SINCRONIZAÇÃO INTELIGENTE ---'))

        with connection.cursor() as cursor:

            # ----------------------------------------------------------------
            # Helpers
            # ----------------------------------------------------------------
            def column_exists(table, column):
                cursor.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name=%s AND column_name=%s
                """, [table, column])
                return cursor.fetchone() is not None

            def table_exists(table):
                cursor.execute("""
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name=%s
                """, [table])
                return cursor.fetchone() is not None

            def fake_migration(app, name):
                cursor.execute(
                    "SELECT 1 FROM django_migrations WHERE app=%s AND name=%s",
                    [app, name]
                )
                if not cursor.fetchone():
                    self.stdout.write(f'  Fakando migração: {name}')
                    cursor.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now())",
                        [app, name]
                    )

            def get_applied_migrations(app):
                cursor.execute(
                    "SELECT name FROM django_migrations WHERE app=%s ORDER BY name",
                    [app]
                )
                return {row[0] for row in cursor.fetchall()}

            # ----------------------------------------------------------------
            # AUTO-HEALING: Preenche gaps na cadeia de migrações do app 'core'
            # Se a migração N+1 está aplicada mas N não está, marca N como fake
            # para que o Django não detecte InconsistentMigrationHistory.
            # ----------------------------------------------------------------
            self.stdout.write('Verificando gaps na cadeia de migrações...')
            applied = get_applied_migrations('core')

            # Pares (dependência_que_falta, migração_que_depende_dela)
            # Detectados automaticamente: migrações conhecidas que foram inseridas
            # retroativamente na cadeia de produção.
            known_gaps = [
                # (migração faltando, migração dependente que já está aplicada)
                ('0069_rh_colaborador_campos_brisoftid', '0070_add_empresa_model'),
                ('0095_brisoftiabase', '0096_adiciona_base_auditoria_e_campos_ia'),
            ]

            for missing, dependent in known_gaps:
                if dependent in applied and missing not in applied:
                    self.stdout.write(
                        f'  Gap detectado: {dependent} aplicada sem {missing}'
                    )
                    fake_migration('core', missing)

            # ----------------------------------------------------------------
            # Migrações fixas que sempre devem ser marcadas como fake
            # (tabelas criadas manualmente ou que já existem no banco)
            # ----------------------------------------------------------------
            self.stdout.write('Marcando migrações de tabelas pré-existentes...')
            always_fake = [
                '0013_cartao_membros_cartaoanexo_cartaocomentario_and_more',
                '0025_chat_models',
                '0030_kanban_models',
            ]
            for name in always_fake:
                fake_migration('core', name)

            # ----------------------------------------------------------------
            # Verificações de colunas específicas (compatibilidade legada)
            # ----------------------------------------------------------------
            if column_exists('core_colaborador', 'bairro'):
                self.stdout.write('  Coluna bairro já existe em core_colaborador.')
                fake_migration('core', '0069_rh_colaborador_campos_brisoftid')

            if column_exists('core_department', 'fluxo_aprovacao'):
                self.stdout.write('  Coluna fluxo_aprovacao já existe em core_department.')
                fake_migration('core', '0072_department_fluxo_aprovacao')

            if column_exists('core_department', 'show_in_nav'):
                self.stdout.write('  Coluna show_in_nav já existe em core_department.')
                fake_migration('core', '0073_department_show_in_nav')

            if table_exists('core_brisoftiabase'):
                self.stdout.write('  Tabela core_brisoftiabase já existe.')
                fake_migration('core', '0095_brisoftiabase')

            # ----------------------------------------------------------------
            # Limpeza de índices residuais
            # ----------------------------------------------------------------
            self.stdout.write('Limpando índices residuais...')
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555 CASCADE;")
            cursor.execute("DROP INDEX IF EXISTS core_storeauditissue_status_f5972555_like CASCADE;")

            # ----------------------------------------------------------------
            # Auto-healing: garantir existência de tabelas do Chat e Kanban
            # ----------------------------------------------------------------
            self.stdout.write('Verificando tabelas do Chat e Kanban...')

            # Tabelas do Chat
            cursor.execute("CREATE TABLE IF NOT EXISTS core_conversation (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_conversation_participants (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, conversation_id BIGINT NOT NULL, user_id BIGINT NOT NULL, UNIQUE(conversation_id, user_id))")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_message (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, content TEXT NOT NULL, is_read BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL, conversation_id BIGINT NOT NULL, sender_id BIGINT NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_useronlinestatus (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, is_online BOOLEAN NOT NULL DEFAULT FALSE, last_seen TIMESTAMPTZ NOT NULL, user_id BIGINT NOT NULL UNIQUE)")

            # Tabelas do Kanban
            cursor.execute("CREATE TABLE IF NOT EXISTS core_quadroetiqueta (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, nome VARCHAR(50) NOT NULL, cor VARCHAR(20) NOT NULL, department_id BIGINT NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_lista (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, titulo VARCHAR(100) NOT NULL, ordem INTEGER NOT NULL DEFAULT 0, archived BOOLEAN NOT NULL DEFAULT FALSE, department_id BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_cartao (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, titulo VARCHAR(200) NOT NULL, descricao TEXT NOT NULL, ordem INTEGER NOT NULL DEFAULT 0, prioridade VARCHAR(20) NOT NULL DEFAULT 'media', archived BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL, criado_por_id BIGINT NOT NULL, lista_id BIGINT NOT NULL, responsavel_id BIGINT, department_id BIGINT NOT NULL, checklists JSONB NOT NULL DEFAULT '[]', cover_color VARCHAR(20) NOT NULL DEFAULT '', data_limite DATE, tags VARCHAR(200) NOT NULL DEFAULT '')")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_cartao_membros (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, cartao_id BIGINT NOT NULL, user_id BIGINT NOT NULL, UNIQUE(cartao_id, user_id))")
            cursor.execute("CREATE TABLE IF NOT EXISTS core_cartao_etiquetas (id BIGINT PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, cartao_id BIGINT NOT NULL, quadroetiqueta_id BIGINT NOT NULL, UNIQUE(cartao_id, quadroetiqueta_id))")

        self.stdout.write(self.style.SUCCESS('--- SINCRONIZAÇÃO CONCLUÍDA ---'))
