import os
import sys
import django
from django.conf import settings

# Adicionar diretório atual ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Configurar settings mínimos
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='secrettestkey',
        STATIC_URL='/static/',
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'core',  # App core
        ]
    )

django.setup()

from django.template.loader import get_template
from django.template import Context, RequestContext
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

def validate_template(template_name):
    print(f"--- Validando {template_name} ---")
    try:
        t = get_template(template_name)
        print(f"LOAD SUCESSO: {template_name} carregado.")
        
        print("Tentando renderizar...")
        # Criar um request fake para contexto
        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        
        # Contexto basico
        context = {
            'user': request.user,
            'messages': [],
            # Adicionar variaveis que podem ser usadas em ifs
            'pending_issues': [],
            'play_sound': False,
        }
        
        rendered = t.render(context, request)
        print(f"RENDER SUCESSO: {template_name} renderizado (tamanho: {len(rendered)} chars).")
        
    except Exception as e:
        print(f"ERRO DE RENDERIZAÇÃO em {template_name}:")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    with open('validation.log', 'w', encoding='utf-8') as f:
        sys.stdout = f
        sys.stderr = f
        validate_template('core/verificacao_lojas.html')
