import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus.settings')
sys.path.append(os.getcwd())
django.setup()

from core.models import User
from django.contrib.auth import authenticate

def debug_users():
    # Force UTF-8 for printing
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)
    
    print(f"--- DEBUGGING SUPABASE USERS ---")
    users = User.objects.all()
    print(f"Total Users: {users.count()}")
    
    for u in users:
        try:
            print(f"ID: {u.id} | User: {u.username} | Email: {u.email} | Active(is_active): {u.is_active} | Ativo: {u.ativo}")
        except Exception:
            print(f"ID: {u.id} | User: [Encoding Error]")
        
    # Test authentication for the admin user if we know the password
    # From environment provided: jeffersonbrito2455@gmail.com / @Lionnees14
    test_email = 'jeffersonbrito2455@gmail.com'
    test_pass = '@Lionnees14'
    
    user = User.objects.filter(email__iexact=test_email).first()
    if user:
        print(f"\nTesting Auth for {test_email} (found user: {user.username})...")
        auth_user = authenticate(username=user.username, password=test_pass)
        if auth_user:
            print(f"✅ Auth SUCCESS for {user.username}")
        else:
            print(f"❌ Auth FAILED for {user.username}")
            # Check why it might have failed
            if not user.is_active:
                print(f"   Reason: User is_active=False")
            if not user.ativo:
                print(f"   Reason: User custom field ativo=False")
    else:
        print(f"\n❌ User with email {test_email} NOT FOUND in Supabase.")

if __name__ == "__main__":
    debug_users()
