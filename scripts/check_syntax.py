import django
from django.template import Template, Context
from django.conf import settings
import os
import re

# Configuração mínima
if not settings.configured:
    settings.configure(TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates'}])
django.setup()

print("--- Teste Unitário Sintaxe ---")
try:
    t = Template("{{ val|default: 0 }}")
    print("Sucesso com espaço: {{ val|default: 0 }}")
except Exception as e:
    print(f"Erro com espaço: {e}")

try:
    t = Template("{{ val|default }}")
    print("Sucesso sem arg: {{ val|default }}")
except Exception as e:
    print(f"Erro sem arg: {e}")

print("\n--- Busca Global por 'default' sem argumentos ---")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE_DIR, 'templates')

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex para default sem argumento (pode falhar, mas tenta pegar casos óbvios)
            # Procura por `|default` seguido de `}}` ou espaço e depois `}}`
            # ou `|default` e nada de `:` antes do fechamento
            
            # Vamos iterar sobre todos os defaults e ver se parecem suspeitos
            matches = re.finditer(r'\|default(?::\s*[^}\s]+)?', content)
            for m in matches:
                snippet = content[max(0, m.start()-10):min(len(content), m.end()+10)]
                # Se não tem dois pontos
                if ':' not in m.group(0):
                     print(f"SUSPEITO em {file}: ...{snippet.replace(chr(10), ' ')}...")
