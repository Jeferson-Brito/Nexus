import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brisoft.settings')
django.setup()

from core.models import User

def check_users():
    users = User.objects.all()
    print(f"Total users: {users.count()}")
    for user in users:
        print(f"ID: {user.id} | Username: {user.username} | Email: {user.email} | Ativo: {user.ativo} | Is Active: {user.is_active}")

if __name__ == "__main__":
    check_users()
