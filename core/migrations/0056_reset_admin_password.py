from django.db import migrations
from django.contrib.auth.hashers import make_password


def reset_all_passwords(apps, schema_editor):
    """
    Emergency recovery: use apps.get_model() properly with make_password
    so this works correctly within the migration historical state.
    Resets:
      - jeffersonbrito2455@gmail.com -> Nexus@2025
      - All admin/gestor users -> Nexus@2025
    """
    User = apps.get_model('core', 'User')
    new_hash = make_password('Nexus@2025')

    reset_count = 0

    # Reset the main admin account
    updated = User.objects.filter(email='jeffersonbrito2455@gmail.com').update(
        password=new_hash,
        is_active=True,
        ativo=True,
    )
    if updated:
        print(f'[0056] OK Password reset for jeffersonbrito2455@gmail.com')
        reset_count += updated
    else:
        print('[0056] WARNING jeffersonbrito2455@gmail.com not found')

    # Reset all admin and gestor accounts
    updated = User.objects.filter(
        role__in=['administrador', 'gestor']
    ).exclude(
        email='jeffersonbrito2455@gmail.com'
    ).update(
        password=new_hash,
        ativo=True,
    )
    print(f'[0056] OK Reset {updated} admin/gestor accounts')
    reset_count += updated

    print(f'[0056] Total: {reset_count} passwords reset to Nexus@2025')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_add_auditoria_feedback_fields'),
    ]

    operations = [
        migrations.RunPython(reset_all_passwords, migrations.RunPython.noop),
    ]
