from django.db import migrations


def remove_cs_clientes(apps, schema_editor):
    Department = apps.get_model('core', 'Department')
    User = apps.get_model('core', 'User')
    Colaborador = apps.get_model('core', 'Colaborador')

    nrs_suporte = Department.objects.filter(slug='nrs-suporte').first()
    cs_clientes = Department.objects.filter(slug='cs-clientes').first()

    if cs_clientes:
        if nrs_suporte:
            # Migra Users vinculados ao CS Clientes
            User.objects.filter(department=cs_clientes).update(department=nrs_suporte)
            # Migra Colaboradores vinculados ao CS Clientes
            Colaborador.objects.filter(department=cs_clientes).update(department=nrs_suporte)
        cs_clientes.delete()


def reverse_remove_cs_clientes(apps, schema_editor):
    Department = apps.get_model('core', 'Department')
    Department.objects.get_or_create(
        slug='cs-clientes',
        defaults={'name': 'CS Clientes', 'description': 'Central de Relacionamento com Clientes'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0107_remove_cardactivity_card_remove_cardactivity_user_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_cs_clientes, reverse_code=reverse_remove_cs_clientes),
    ]
