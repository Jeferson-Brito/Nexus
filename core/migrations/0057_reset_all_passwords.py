from django.db import migrations
from django.contrib.auth.hashers import make_password


def reset_passwords_v2(apps, schema_editor):
    """
    Second emergency attempt: migration 0056 may have already been marked
    as applied (even if it failed). This migration 0057 does the same thing
    using the correct apps.get_model() + make_password() approach.
    """
    User = apps.get_model('core', 'User')
    new_hash = make_password('Nexus@2025')

    reset_count = 0

    # Reset ALL users so nobody is locked out
    all_count = User.objects.all().update(
        password=new_hash,
        is_active=True,
        ativo=True,
    )
    reset_count = all_count
    print(f'[0057] OK Reset {reset_count} user passwords to Nexus@2025')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0056_reset_admin_password'),
    ]

    operations = [
        migrations.RunPython(reset_passwords_v2, migrations.RunPython.noop),
    ]
