from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Lista os usuários cadastrados e seu status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- LISTAGEM DE USUÁRIOS ---'))
        
        users = User.objects.all()
        for u in users:
            self.stdout.write(f"Usuário: {u.username} | Email: {u.email} | Role: {u.role} | Ativo: {u.is_active}/{u.ativo} | Staff: {u.is_staff} | Super: {u.is_superuser}")
        
        self.stdout.write(self.style.SUCCESS('--- FIM DA LISTAGEM ---'))
