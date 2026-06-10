from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = "Fix duplicate permissions + ensure critical schema columns exist"

    # Colunas críticas que devem existir no banco
    REQUIRED_COLUMNS = [
        ("core_department", "fluxo_aprovacao", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("core_department", "show_in_nav", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ]

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # =============================================
            # PARTE 1: Garantir colunas críticas (Auto-healing)
            # =============================================
            self.stdout.write("==> [fix_permissions] Verificando esquema do banco...")
            for table, column, col_def in self.REQUIRED_COLUMNS:
                try:
                    sql = f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column}" {col_def}'
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS(f"  [OK] {table}.{column} OK"))
                except Exception as e:
                    err = str(e)
                    if "already exists" in err or "duplicate" in err.lower():
                        self.stdout.write(f"  [OK] {table}.{column} já existe")
                    else:
                        self.stdout.write(self.style.ERROR(f"  [FAIL] {table}.{column}: {err}"))

            # =============================================
            # PARTE 2: Remover permissões duplicadas
            # =============================================
            self.stdout.write("==> [fix_permissions] Verificando permissões duplicadas...")

            # Verifica se a tabela auth_permission existe antes de prosseguir
            cursor.execute("SELECT to_regclass('public.auth_permission')")
            duplicates = []
            if not cursor.fetchone()[0]:
                self.stdout.write(self.style.WARNING("  ! Tabela auth_permission ainda não existe. Pulando limpeza de permissões."))
            else:
                cursor.execute("""
                    SELECT content_type_id, codename, COUNT(*)
                    FROM auth_permission
                    GROUP BY content_type_id, codename
                    HAVING COUNT(*) > 1
                """)
                duplicates = cursor.fetchall()

            if not duplicates:
                self.stdout.write(self.style.SUCCESS("  [OK] Nenhuma permissão duplicada encontrada."))
            else:
                for ct_id, codename, count in duplicates:
                    self.stdout.write(self.style.WARNING(f"  Corrigindo {count} duplicatas para {codename} (CT: {ct_id})"))

                    cursor.execute("""
                        SELECT id FROM auth_permission
                        WHERE content_type_id = %s AND codename = %s
                        ORDER BY id ASC
                    """, [ct_id, codename])
                    ids = [row[0] for row in cursor.fetchall()]

                    ids_to_delete = ids[1:]
                    if ids_to_delete:
                        cursor.execute("DELETE FROM auth_permission WHERE id = ANY(%s)", [ids_to_delete])

            self.stdout.write(self.style.SUCCESS("==> [fix_permissions] Concluído."))

        # =============================================
        # PARTE 3: Garantir show_in_nav nos departamentos funcionais
        # =============================================
        self.stdout.write("==> [fix_permissions] Ativando departamentos no menu...")
        try:
            Department = apps.get_model('core', 'Department')

            # Departamentos funcionais que devem existir e aparecer no menu
            functional_departments = [
                {'slug': 'escala',            'name': 'Escala',            'description': 'Escala de Trabalho'},
                {'slug': 'ponto-eletronico',  'name': 'Ponto Eletrônico',  'description': 'Ponto Eletrônico'},
            ]

            for dept in functional_departments:
                obj, created = Department.objects.get_or_create(
                    slug=dept['slug'],
                    defaults={'name': dept['name'], 'description': dept['description'], 'show_in_nav': True}
                )
                if not obj.show_in_nav:
                    obj.show_in_nav = True
                    obj.save(update_fields=['show_in_nav'])
                status = "criado" if created else "atualizado"
                self.stdout.write(self.style.SUCCESS(f"  [OK] {obj.name} ({status})"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] Erro ao criar departamentos oficiais: {e}"))

        # =============================================
        # PARTE 4: Deletar TODOS os departamentos legados (SEMPRE, sem condição)
        # =============================================
        self.stdout.write("==> [fix_permissions] Removendo departamentos legados do banco...")
        try:
            Department = apps.get_model('core', 'Department')
            User = apps.get_model('core', 'User')

            # Migrar usuários de departamentos não-oficiais para None
            User.objects.exclude(
                department__slug__in=['escala', 'ponto-eletronico']
            ).update(department=None)

            # Deletar TODOS os departamentos que não sejam os dois oficiais
            # Esta operação é SEMPRE executada, independente de qualquer condição.
            legados = Department.objects.exclude(slug__in=['escala', 'ponto-eletronico'])
            nomes_legados = list(legados.values_list('name', flat=True))
            deleted_count, _ = legados.delete()

            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] Removidos {deleted_count} departamento(s) legado(s): {nomes_legados}"
                ))
            else:
                self.stdout.write(self.style.SUCCESS("  [OK] Nenhum departamento legado encontrado."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] Erro ao remover departamentos legados: {e}"))
            # Fallback: tentar via SQL direto
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_department WHERE slug NOT IN ('escala', 'ponto-eletronico')"
                    )
                    self.stdout.write(self.style.SUCCESS("  [OK] Fallback SQL executado com sucesso."))
            except Exception as sql_err:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Fallback SQL falhou: {sql_err}"))
