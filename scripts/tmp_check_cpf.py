import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import Colaborador

cpf = '70636612481'
print(f"Buscando colaborador com CPF: {cpf}")

try:
    c = Colaborador.objects.get(cpf=cpf)
    print(f"ENCONTRADO: ID={c.id}, Nome={c.nome_completo}, Status={c.status}")
except Colaborador.DoesNotExist:
    print("Nenhum colaborador encontrado com este CPF.")
except Exception as e:
    print(f"Erro ao buscar: {str(e)}")
