import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

project_root = r"c:\Users\jeffe\Documents\Sites\Nexus"
if project_root not in sys.path:
    sys.path.append(project_root)

from gestao_reclame_aqui import settings as app_settings

if not settings.configured:
    settings_dict = {}
    for key in dir(app_settings):
        if key.isupper():
            settings_dict[key] = getattr(app_settings, key)
    
    # Remove 'storages' to avoid dependency issues during migration
    if 'storages' in settings_dict.get('INSTALLED_APPS', []):
        settings_dict['INSTALLED_APPS'] = [app for app in settings_dict['INSTALLED_APPS'] if app != 'storages']
        
    if 'STORAGES' in settings_dict:
        settings_dict['STORAGES'] = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }

    settings.configure(**settings_dict)

django.setup()

print("Making migrations...")
call_command('makemigrations', 'core')
print("Migrating...")
call_command('migrate', 'core')
print("Done.")
