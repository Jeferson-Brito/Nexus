import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus.settings')
django.setup()

from core.models import Colaborador, User, Department, Cargo, CentroCusto, Empresa

def check_rh_data():
    print("Checking Colaboradores...")
    colabs = Colaborador.objects.all()
    print(f"Total: {colabs.count()}")
    for c in colabs:
        try:
            print(f"ID: {c.id}, Nome: {c.nome_completo}")
            print(f"  Admissao: {c.data_admissao}")
            print(f"  Tempo Empresa: {c.tempo_empresa}")
            print(f"  Department: {c.department}")
            print(f"  Cargo: {c.cargo_atual}")
        except Exception as e:
            print(f"  ERROR for {c.id}: {str(e)}")

    print("\nChecking Users without card...")
    users = User.objects.filter(ativo=True).filter(colaborador_perfil__isnull=True)
    print(f"Total: {users.count()}")
    for u in users:
        try:
            print(f"ID: {u.id}, Username: {u.username}")
            print(f"  Department: {u.department}")
        except Exception as e:
            print(f"  ERROR for {u.id}: {str(e)}")

    print("\nChecking Departments...")
    depts = Department.objects.all()
    for d in depts:
        print(f"ID: {d.id}, Name: {d.name}, Slug: {d.slug}, show_in_nav: {d.show_in_nav}, fluxo: {d.fluxo_aprovacao}")

if __name__ == "__main__":
    check_rh_data()
