"""
ASGI config for nexus project.
Simple ASGI application (no channels/websockets).
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus.settings')

application = get_asgi_application()
