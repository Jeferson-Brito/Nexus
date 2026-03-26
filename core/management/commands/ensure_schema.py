from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Garante que colunas críticas existam no banco de dados usando ALTER TABLE IF NOT EXISTS"

    # Lista de correções: (tabela, coluna, definição SQL da coluna)
    REQUIRED_COLUMNS = [
        ("core_department", "fluxo_aprovacao", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("core_department", "show_in_nav", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ]

    def handle(self, *args, **options):
        self.stdout.write("==> ensure_schema: Verificando colunas críticas...")
        
        with connection.cursor() as cursor:
            for table, column, col_def in self.REQUIRED_COLUMNS:
                try:
                    # CockroachDB suporta IF NOT EXISTS em ADD COLUMN
                    sql = f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column}" {col_def}'
                    self.stdout.write(f"  Executando: {sql}")
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {table}.{column} OK"))
                except Exception as e:
                    err = str(e)
                    # Se o erro for "column already exists", é ok
                    if "already exists" in err or "duplicate column" in err.lower():
                        self.stdout.write(self.style.SUCCESS(f"  ✓ {table}.{column} já existe"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ Erro em {table}.{column}: {err}"))

        self.stdout.write(self.style.SUCCESS("==> ensure_schema: Concluído."))
