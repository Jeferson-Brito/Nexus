from django.db import migrations, connection

def force_text_fields(apps, schema_editor):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("""
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_apresentacao TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_historico TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_entendimento TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_informacao TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_acordo_espera TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_respeito TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_portugues TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_finalizacao TYPE text;
            ALTER TABLE core_auditoriaatendimento ALTER COLUMN imagem_erro_procedimento TYPE text;
            """)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_change_image_fields_to_text'),
    ]

    operations = [
        migrations.RunPython(force_text_fields, migrations.RunPython.noop),
    ]
