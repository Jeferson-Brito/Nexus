# Migration definitiva: garante que APENAS Escala e Ponto Eletrônico existem no banco.
# Esta migration é idempotente e pode rodar quantas vezes for necessário com segurança.

from django.db import migrations


def enforce_clean_departments(apps, schema_editor):
    """
    Garante que apenas os departamentos 'Escala' e 'Ponto Eletrônico' existam.
    Remove fisicamente qualquer outro departamento do banco de dados.
    Esta função é idempotente.
    """
    Department = apps.get_model('core', 'Department')
    User = apps.get_model('core', 'User')

    # 1. Garantir que 'Escala' existe
    escala, _ = Department.objects.get_or_create(
        slug='escala',
        defaults={
            'name': 'Escala',
            'description': 'Escala de Trabalho',
            'show_in_nav': True,
        }
    )
    # Garantir que está visível no nav, mesmo que já exista
    if not escala.show_in_nav or escala.name != 'Escala':
        escala.name = 'Escala'
        escala.show_in_nav = True
        escala.save()

    # 2. Garantir que 'Ponto Eletrônico' existe
    ponto, _ = Department.objects.get_or_create(
        slug='ponto-eletronico',
        defaults={
            'name': 'Ponto Eletrônico',
            'description': 'Ponto Eletrônico',
            'show_in_nav': True,
        }
    )
    if not ponto.show_in_nav or ponto.name != 'Ponto Eletrônico':
        ponto.name = 'Ponto Eletrônico'
        ponto.show_in_nav = True
        ponto.save()

    # 3. Migrar usuários de departamentos legados para None
    User.objects.exclude(
        department__slug__in=['escala', 'ponto-eletronico']
    ).update(department=None)

    # 4. Deletar TODOS os departamentos que não são os dois oficiais
    deleted_count, _ = Department.objects.exclude(
        slug__in=['escala', 'ponto-eletronico']
    ).delete()

    if deleted_count:
        print(f"[0116] Removidos {deleted_count} departamento(s) legado(s).")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0115_remove_message_conversation_remove_evento_department_and_more'),
    ]

    operations = [
        migrations.RunPython(enforce_clean_departments, migrations.RunPython.noop),
    ]
