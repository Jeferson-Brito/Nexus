import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus.settings')
django.setup()

from core.models import Colaborador, User, Department, Cargo, CentroCusto, Empresa
from django.db import connection

def check_rh_data():
    try:
        print(f"Colaboradores count: {Colaborador.objects.count()}")
        print(f"Active Colaboradores: {Colaborador.objects.filter(status='ativo').count()}")
        
        print("\nColaboradores details (first 5):")
        for c in Colaborador.objects.all()[:5]:
            print(f"- {c.nome_completo} (ID: {c.id}, Status: {c.status}, Dept: {c.department})")

        print(f"\nUsers count: {User.objects.count()}")
        print(f"Active Users: {User.objects.filter(ativo=True).count()}")
        
        users_sem_ficha = User.objects.filter(ativo=True).filter(colaborador_perfil__isnull=True)
        print(f"Users sem ficha count: {users_sem_ficha.count()}")
        
        print("\nAdmins without ficha:")
        admins_sem_ficha = users_sem_ficha.filter(role='administrador')
        print(f"Count: {admins_sem_ficha.count()}")
        for u in admins_sem_ficha:
            print(f"- {u.username} (ID: {u.id}, Email: {u.email}, Dept: {u.department})")

        print("\nChecking for potential NULL issues:")
        null_admissao = Colaborador.objects.filter(data_admissao__isnull=True).count()
        print(f"Colaboradores with NULL data_admissao: {null_admissao}")
        
    except Exception as e:
        print(f"Error during check: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    check_rh_data()
