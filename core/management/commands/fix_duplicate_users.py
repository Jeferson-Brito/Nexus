from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Corrige os usuários com email conflict_ gerados pelo init_production antigo'

    def handle(self, *args, **options):
        conflicts = User.objects.filter(email__startswith='conflict_')
        if not conflicts.exists():
            self.stdout.write(self.style.SUCCESS('Nenhum usuário com email conflict_ encontrado.'))
            return
            
        for conflict in conflicts:
            original_email = conflict.email.split('_', 2)[-1]
            
            dup_user = User.objects.filter(email=original_email).first()
            if dup_user and dup_user.id != conflict.id:
                self.stdout.write(self.style.WARNING(f"Apagando o duplicado recém-criado {dup_user.username} - {dup_user.email}"))
                dup_user.delete()
                
            self.stdout.write(self.style.SUCCESS(f"Restaurando e-mail de {conflict.username} para {original_email}"))
            conflict.email = original_email
            conflict.save()

        self.stdout.write(self.style.SUCCESS('\nLimpeza de usuários concluída!'))
