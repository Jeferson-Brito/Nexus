from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

class Command(BaseCommand):
    help = "Emergency: reset all user passwords to Brisoft@2025 and ensure admin exists"

    def handle(self, *args, **options):
        import sys
        from django.db import connection
        
        try:
            db_info = connection.settings_dict
            self.stdout.write(self.style.NOTICE(f"DB CONFIG: host={db_info.get('HOST')}, database={db_info.get('NAME')}"))
            
            User = get_user_model()
            new_hash = make_password('Brisoft@2025')

            self.stdout.write(self.style.NOTICE("Starting emergency password reset diagnostic..."))

            # 1. Diagnostic: List all users
            all_users = User.objects.all()
            user_count = all_users.count()
            self.stdout.write(self.style.WARNING(f'Total users in DB: {user_count}'))
            
            for u in all_users:
                self.stdout.write(f'  [USER] id={u.id}, email="{u.email}", username="{u.username}", role="{u.role}", active={u.is_active}/{u.ativo}')

            # 2. Ensure specific admin exists
            admin_email = 'jeffersonbrito2455@gmail.com'
            admin_user = User.objects.filter(email__iexact=admin_email).first()
            
            if not admin_user:
                self.stdout.write(self.style.WARNING(f'User {admin_email} NOT FOUND. Creating a new one...'))
                # Try to see if username 'jefferson' exists first to avoid conflict
                username = 'jefferson'
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f'jefferson{suffix}'
                    suffix += 1
                
                admin_user = User.objects.create(
                    username=username,
                    email=admin_email,
                    password=new_hash,
                    role='administrador',
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                    ativo=True
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Created fresh admin user: {admin_user.email} (username={admin_user.username})'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Found existing admin user {admin_user.email}. Updating...'))
                admin_user.is_active = True
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.ativo = True
                admin_user.password = new_hash
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Updated existing admin user: {admin_user.email}'))

            # 3. Reset all other passwords
            count = User.objects.all().update(
                password=new_hash,
                is_active=True,
                ativo=True
            )

            self.stdout.write(self.style.SUCCESS(
                f'✅ Emergency password reset SUCCESS: {count} total users processed.'
            ))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ CRITICAL ERROR in reset_passwords: {e}"))
            import traceback
            traceback.print_exc()
