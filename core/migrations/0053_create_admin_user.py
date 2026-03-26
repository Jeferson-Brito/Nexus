from django.db import migrations


def create_admin_user(apps, schema_editor):
    User = apps.get_model('core', 'User')
    if User.objects.filter(username='admin').exists():
        # Atualiza role e is_superuser se o usuário já existir
        User.objects.filter(username='admin').update(
            role='administrador',
            is_superuser=True,
            is_staff=True,
        )
        return

    from django.contrib.auth.hashers import make_password
    user = User(
        username='admin',
        email='admin@nexus.com',
        first_name='Admin',
        last_name='',
        role='administrador',
        is_superuser=True,
        is_staff=True,
        is_active=True,
        ativo=True,
        password=make_password('Admin123')
    )
    user.save()


def reverse_create_admin(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(username='admin', email='admin@nexus.com').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_enable_rls_all_tables'),
    ]

    operations = [
        migrations.RunPython(create_admin_user, reverse_code=reverse_create_admin),
    ]
