import os
import sys
import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brisoft.settings')
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
