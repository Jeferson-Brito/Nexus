
import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
import json

# Setup Django Environment
project_root = r"c:\Users\jeffe\Documents\Sites\Nexus"
if project_root not in sys.path:
    sys.path.append(project_root)

# Manually configure settings to bypass storages
from gestao_reclame_aqui import settings as app_settings

if not settings.configured:
    settings_dict = {}
    for key in dir(app_settings):
        if key.isupper():
            settings_dict[key] = getattr(app_settings, key)
    
    # Remove 'storages' to avoid dependency issues
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

from core.models import SystemNotification, User
from core.views import api_get_system_notifications

# Create a dummy user for login_required
user = User.objects.filter(is_superuser=True).first()
if not user:
    # fallback if no superuser
    user = User.objects.first()

if not user:
    print("No user found to test with.")
    sys.exit(1)

# Create a sample notification
print("Creating sample notification...")
notif = SystemNotification.objects.create(
    title="Test Notification",
    message="This is a test notification.",
    details="<p>Reviewing the system notification feature.</p>",
    category="system"
)

# Create request
factory = RequestFactory()
request = factory.get('/api/system/notifications/')
request.user = user

# Call view
print("Calling API view...")
response = api_get_system_notifications(request)

# Check response
if response.status_code == 200:
    content = json.loads(response.content)
    print("Response Content:", json.dumps(content, indent=2))
    
    # Verify content
    found = False
    for n in content['notifications']:
        if n['id'] == notif.id:
            found = True
            print("SUCCESS: Created notification found in response.")
            break
    
    if not found:
        print("FAILURE: Notification not found in response.")
else:
    print(f"FAILURE: Status code {response.status_code}")

# Cleanup
print("Cleaning up...")
notif.delete()
print("Done.")
