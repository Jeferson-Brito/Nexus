import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import Colaborador

cpf = '70636612481'
print(f"Tentando excluir colaborador com CPF: {cpf}")

try:
    c = Colaborador.objects.get(cpf=cpf)
    print(f"Encontrado: {c.nome_completo} (ID: {c.id})")
    c.delete()
    print("Sucesso! Registro excluído.")
except Colaborador.DoesNotExist:
    print("Colaborador não encontrado.")
except Exception as e:
    print(f"ERRO AO EXCLUIR: {str(e)}")
