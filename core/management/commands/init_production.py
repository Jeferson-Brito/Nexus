"""
Comando para inicializar o sistema em produção.
Executa migrações e cria usuário admin automaticamente.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Inicializa o sistema em produção: executa migrações e cria usuário admin'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando configuração do sistema...'))
        
        # Executar migrações
        self.stdout.write(self.style.WARNING('Executando migrações...'))
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✓ Migrações executadas com sucesso!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Erro ao executar migrações: {e}'))
            # Não retornar aqui, tentar seguir para garantir o esquema manualmente
            
        # Garantir esquema manual (Self-healing)
        self.stdout.write(self.style.WARNING('Verificando integridade do esquema...'))
        try:
            call_command('ensure_schema')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Erro ao garantir esquema: {e}'))
        
        # Criar usuário admin
        self.stdout.write(self.style.WARNING('Criando usuário administrador...'))
        try:
            # Pegar dados do ambiente com fallback para os valores do usuário
            email = os.environ.get('ADMIN_EMAIL', 'jeffersonbrito2455@gmail.com')
            password = os.environ.get('ADMIN_PASSWORD', '@Lionnees14')
            username = os.environ.get('ADMIN_USERNAME', email.split('@')[0])
            first_name = 'Jeferson'
            last_name = 'Brito'
            role = 'administrador' # Mudado para administrador conforme User.ROLE_CHOICES
            ativo = True

            # Buscar primeiro pelo e-mail para evitar criar duplicatas ou renomear e-mails existentes
            user = User.objects.filter(email__iexact=email).first()
            
            if user:
                # Se o usuário já existe com este e-mail, apenas atualiza suas permissões e mantém o username original
                user.first_name = first_name
                user.last_name = last_name
                user.role = role
                user.ativo = ativo
                user.is_staff = True
                user.is_superuser = True
                user.save()
                created = False
                username = user.username  # Atualiza a variável para exibir no log corretamente
            else:
                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'role': role,
                        'ativo': ativo,
                        'is_staff': True,
                        'is_superuser': True,
                    }
                )
            
            # Forçar a senha sempre que o comando rodar (para garantir acesso se as env vars mudarem)
            user.set_password(password)
            user.save()

            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Usuário {username} criado com sucesso!'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Usuário {username} atualizado com sucesso!'))

            self.stdout.write(self.style.SUCCESS('\nCredenciais de acesso:'))
            self.stdout.write(self.style.SUCCESS(f'Usuário: {username}'))
            self.stdout.write(self.style.SUCCESS(f'E-mail: {email}'))
            self.stdout.write(self.style.SUCCESS(f'Senha: (protegida)'))
            self.stdout.write(self.style.SUCCESS(f'Perfil: {role.capitalize()}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Erro ao criar usuário: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sistema inicializado com sucesso!'))

