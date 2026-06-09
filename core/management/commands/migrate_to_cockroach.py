"""
Management command to migrate all data from Supabase (source) to CockroachDB (default).

Usage:
    Set SOURCE_DATABASE_URL env var to the Supabase connection string, then run:
        python manage.py migrate_to_cockroach

The command copies data table by table, respecting FK order.
"""

import os
import psycopg2
import psycopg2.extras
from django.core.management.base import BaseCommand
from django.db import connection


# Tables in dependency order (parents before children to respect FKs)
TABLES_IN_ORDER = [
    # Django internals
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    # Core: basic data
    "core_department",
    "core_turno",
    "core_store",
    # Core: users (depends on department)
    # Core: users (depends on department)
    "core_user",
    "core_user_groups",
    "core_user_user_permissions",
    # Core: basic operational data
    "core_complaint",
    "core_activity",
    "core_auditlog",
    # Other core tables
    "core_evento",
    "core_ferramentaia",
    "core_artigobaseconhecimento",
    "core_observacaodesempenho",
    "core_indicadordesempenho",
    "core_metamensalglobal",
    "core_analistaescala",
    "core_folgamanual",
    # Escala
    "core_escala",

    # Routine / Task
    "core_routine",
    "core_task",
    "core_routinelog",
    # Store audit
    "core_storeauditissue",
    "core_storeaudit",
    "core_storeaudititem",
    "core_storeviewersession",
    "core_configuracaoauditoria",
    "core_auditoriaatendimento",
    # KPI / quota
    "core_weeklyverificationkpi",
    "core_dailyauditquota",
    "core_analystassignment",
    # Notifications
    "core_systemnotification",
]


class Command(BaseCommand):
    help = "Migrates all data from Supabase (SOURCE_DATABASE_URL) to CockroachDB (default DB)"

    def handle(self, *args, **options):
        source_url = os.environ.get("SOURCE_DATABASE_URL")
        
        print("\n--- Iniciando Migração de Dados ---", flush=True)
        
        if not source_url:
            print("❌ ERRO: Variável SOURCE_DATABASE_URL não encontrada!", flush=True)
            return

        print(f"📡 Tentando conectar ao Supabase (IPv4)...", flush=True)
        try:
            # Supabase Pooler geralmente requer sslmode=require
            # Mas tentamos primeiro o padrão da URL (que já deve ter o parâmetro)
            src_conn = psycopg2.connect(source_url)
            print("✅ Conectado ao Supabase com sucesso!", flush=True)
        except Exception as e:
            print(f"⚠️ Tentativa 1 falhou: {e}", flush=True)
            print("📡 Tentando com sslmode='require' forçado...", flush=True)
            try:
                src_conn = psycopg2.connect(source_url, sslmode="require")
                print("✅ Conectado ao Supabase (SSL)!", flush=True)
            except Exception as e2:
                print(f"❌ Falha total na conexão: {e2}", flush=True)
                return

        src_conn.autocommit = True
        src_cur = src_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        tables = [t for t in TABLES_IN_ORDER if t]
        total_copied = 0

        print(f"📋 Total de tabelas para processar: {len(tables)}\n", flush=True)

        for table in tables:
            # Check if table exists in source
            src_cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = %s)",
                [table]
            )
            if not src_cur.fetchone()[0]:
                print(f"  ⚠️  PULANDO: {table} (não existe no Supabase)", flush=True)
                continue

            # Check source rows
            src_cur.execute(f'SELECT COUNT(*) FROM public."{table}"')
            count = src_cur.fetchone()[0]
            if count == 0:
                print(f"  — {table}: vazio no Supabase, pulando", flush=True)
                continue

            print(f"  → Copiando {table} ({count} linhas)...", flush=True)

            # Fetch rows
            src_cur.execute(f'SELECT * FROM public."{table}"')
            rows = src_cur.fetchall()
            columns = [desc[0] for desc in src_cur.description]
            col_list = ", ".join(f'"{c}"' for c in columns)
            
            # Using execute_values for much faster bulk insertion
            from psycopg2.extras import execute_values
            
            with connection.cursor() as dest_cur:
                try:
                    # Clear destination table
                    try:
                        dest_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                    except Exception:
                        dest_cur.execute(f'DELETE FROM "{table}"')
                    
                    # Pre-process rows for JSON fields
                    import json
                    clean_rows = []
                    for row in rows:
                        clean_row = []
                        for val in row:
                            if isinstance(val, (dict, list)):
                                clean_row.append(json.dumps(val))
                            else:
                                clean_row.append(val)
                        clean_rows.append(tuple(clean_row))

                    # Batch insert
                    insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES %s'
                    execute_values(dest_cur, insert_sql, clean_rows)
                    
                    print(f"    ✅ {len(rows)} linhas copiadas para {table}", flush=True)
                    total_copied += len(rows)
                except Exception as e:
                    print(f"    ❌ Erro em {table}: {e}", flush=True)

        src_cur.close()
        src_conn.close()

        print(f"\n✨ MIGRAÇÃO CONCLUÍDA! Total de {total_copied} linhas copiadas.", flush=True)
        print("Lembre-se de remover o comando do Start Command agora.", flush=True)
