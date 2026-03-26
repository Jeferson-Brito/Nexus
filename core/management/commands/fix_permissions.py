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
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {table}.{column} OK"))
                except Exception as e:
                    err = str(e)
                    if "already exists" in err or "duplicate" in err.lower():
                        self.stdout.write(f"  ✓ {table}.{column} já existe")
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ {table}.{column}: {err}"))

            # =============================================
            # PARTE 2: Remover permissões duplicadas
            # =============================================
            self.stdout.write("==> [fix_permissions] Verificando permissões duplicadas...")

            cursor.execute("""
                SELECT content_type_id, codename, COUNT(*)
                FROM auth_permission
                GROUP BY content_type_id, codename
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()

            if not duplicates:
                self.stdout.write(self.style.SUCCESS("  ✓ Nenhuma permissão duplicada encontrada."))
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
                {'slug': 'nrs-suporte', 'name': 'NRS Suporte', 'description': 'Suporte NRS'},
                {'slug': 'cs-clientes', 'name': 'CS Clientes', 'description': 'Customer Success'},
                {'slug': 'rh',          'name': 'RH',          'description': 'Recursos Humanos'},
                {'slug': 'nrp',         'name': 'NRP',         'description': 'NRP'},
                {'slug': 'onboarding',  'name': 'Onboarding',  'description': 'Onboarding'},
                {'slug': 'logistica',   'name': 'Logística',   'description': 'Logística'},
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
                self.stdout.write(self.style.SUCCESS(f"  ✓ {obj.name} ({status})"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Erro ao ativar departamentos: {e}"))
