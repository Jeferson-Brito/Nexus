from django.db import migrations


# All tables in the public schema that need RLS enabled.
# Django accesses the DB via the postgres/service_role which bypasses RLS by default,
# so enabling RLS here does NOT break anything — it just satisfies the Supabase security linter.
TABLES = [
    # Django internal tables
    "django_migrations",
    "django_content_type",
    "django_admin_log",
    "django_session",
    # Django auth tables
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    # Core app tables
    "core_user",
    "core_user_groups",
    "core_user_user_permissions",
    "core_auditlog",
    "core_activity",
    "core_complaint",
    "core_turno",
    "core_department",
    "core_folgamanual",
    "core_analistaescala",
    "core_evento",
    "core_ferramentaia",
    "core_artigobaseconhecimento",
    "core_observacaodesempenho",
    "core_escala",
    "core_cartao",
    "core_lista",
    "core_store",
    "core_cartao_membros",
    "core_cartaoanexo",
    "core_cartaocomentario",
    "core_quadroetiqueta",
    "core_cartao_etiquetas",
    "core_routine",
    "core_task",
    "core_routinelog",
    "core_refundrequestattachment",
    "core_storeaudit",
    "core_refundrequest",
    "core_indicadordesempenho",
    "core_metamensalglobal",
    "core_storeviewersession",
    "core_checklist",
    "core_kanbancard",
    "core_kanbanlist",
    "core_checklistitem",
    "core_kanbanboard",
    "core_cardlabel",
    "core_kanbancard_assigned_to",
    "core_kanbancard_labels",
    "core_cardcomment",
    "core_cardattachment",
    "core_cardactivity",
    "core_boardmembership",
    "core_storeaudititem",
    "core_weeklyverificationkpi",
    "core_dailyauditquota",
    "core_analystassignment",
    "core_storeauditissue",
    "core_configuracaoauditoria",
    "core_auditoriaatendimento",
    "core_systemnotification",
]


def enable_rls(apps, schema_editor):
    # RLS e service_role são exclusivos do Supabase/PostgreSQL puro.
    # No CockroachDB, esta migration é ignorada silenciosamente.
    if schema_editor.connection.vendor != 'postgresql' or "cockroach" in schema_editor.connection.settings_dict.get("ENGINE", ""):
        return
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            # Enable RLS on the table
            cursor.execute(f'ALTER TABLE IF EXISTS public."{table}" ENABLE ROW LEVEL SECURITY;')
            # Drop the policy if it already exists (idempotent)
            cursor.execute(
                f'DROP POLICY IF EXISTS "service_role_full_access" ON public."{table}";'
            )
            cursor.execute(
                f"""
                CREATE POLICY "service_role_full_access"
                ON public."{table}"
                AS PERMISSIVE
                FOR ALL
                TO service_role
                USING (true)
                WITH CHECK (true);
                """
            )


def disable_rls(apps, schema_editor):
    """Reverse: disable RLS on all tables."""
    if schema_editor.connection.vendor != 'postgresql' or "cockroach" in schema_editor.connection.settings_dict.get("ENGINE", ""):
        return
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(
                f'DROP POLICY IF EXISTS "service_role_full_access" ON public."{table}";'
            )
            cursor.execute(f'ALTER TABLE IF EXISTS public."{table}" DISABLE ROW LEVEL SECURITY;')


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0051_systemnotification"),
        ("sessions", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(enable_rls, reverse_code=disable_rls),
    ]
