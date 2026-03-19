import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import Department
from django.utils.text import slugify

def create_logistica():
    name = "Logística"
    slug = slugify(name)
    
    dept, created = Department.objects.get_or_create(
        name=name,
        defaults={'slug': slug, 'description': 'Departamento de Logística'}
    )
    
    if created:
        print(f"Departamento '{name}' criado com sucesso.")
    else:
        print(f"Departamento '{name}' já existe.")

if __name__ == "__main__":
    create_logistica()
