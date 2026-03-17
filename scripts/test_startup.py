import os
import django
import sys
import time

print("Checking environment...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')

try:
    print("Setting up Django...")
    django.setup()
    print("Django setup complete.")
    
    from django.apps import apps
    print("Loading apps...")
    for app in apps.get_app_configs():
        print(f"Loading app: {app.name}")
        apps.get_models(app.label)
    print("Apps loaded.")
    
    print("Checking models...")
    from core.models import User
    print("User model imported.")
except Exception as e:
    print(f"Error during diagnostic: {e}")
    sys.exit(1)
finally:
    print("Diagnostic finished.")
