from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Max, Count
from django.contrib.auth.forms import PasswordChangeForm
from ..models import User, AuditLog

def login_view_custom(request):
    """View customizada de login que verifica se o usuário está ativo e aceita e-mail"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email_raw = request.POST.get('email', '')
        email = email_raw.strip()
        password = request.POST.get('password')
        
        if email and password:
            try:
                # Buscar usuário por e-mail de forma case-insensitive
                user = User.objects.filter(email__iexact=email).first()
                
                if not user:
                    messages.error(request, 'E-mail ou senha incorretos. Tente novamente.')
                    return render(request, 'core/login.html')

                # Autenticar usando o username do usuário encontrado
                auth_user = authenticate(request, username=user.username, password=password)
                
                if auth_user is not None:
                    if auth_user.ativo:
                        login(request, auth_user)
                        # Log access history
                        try:
                            AuditLog.objects.create(
                                usuario=auth_user,
                                action='login',
                                target_type='User',
                                target_id=auth_user.id,
                                detalhes_json={'ip': request.META.get('REMOTE_ADDR'), 'user_agent': request.META.get('HTTP_USER_AGENT')}
                            )
                        except Exception as e:
                            print(f"Error logging login: {e}")
                            
                        messages.success(request, f'Bem-vindo, {auth_user.get_full_name() or auth_user.username}!')
                        next_url = request.GET.get('next', '/')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'Sua conta está inativa. Entre em contato com o administrador.')
                else:
                    messages.error(request, 'E-mail ou senha incorretos. Tente novamente.')
            except Exception as e:
                import traceback
                from django.db import connections
                from django.db.utils import OperationalError
                
                db_conn = connections['default']
                db_info = f"{db_conn.settings_dict.get('HOST')}:{db_conn.settings_dict.get('PORT')}"
                
                print(f"!!! Error in login_view_custom !!!")
                print(f"Database: {db_info}")
                print(f"Exception: {str(e)}")
                traceback.print_exc()
                
                if isinstance(e, OperationalError):
                    error_msg = 'Erro de conexão com o banco de dados. Verifique as configurações no Render.'
                else:
                    error_msg = 'Erro inesperado na autenticação. Tente novamente.'
                    
                messages.error(request, error_msg)
        else:
            messages.error(request, 'Por favor, preencha todos os campos.')
    
    return render(request, 'core/login.html')

def logout_view(request):
    """View customizada para logout que aceita GET"""
    logout(request)
    messages.success(request, 'Você saiu do sistema com sucesso!')
    return redirect('login')

@login_required
def settings_view(request):
    """Página de configurações do usuário"""
    if request.method == 'POST':
        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Manter usuário logado
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('settings')
            else:
                messages.error(request, 'Erro ao alterar senha. Verifique os campos.')
    else:
        password_form = PasswordChangeForm(request.user)

    return render(request, 'core/settings.html', {
        'password_form': password_form
    })

@login_required
def user_access_history(request):
    """Exibe o histórico de acessos dos usuários (apenas Administradores)"""
    if not request.user.is_administrador():
        messages.error(request, 'Acesso não autorizado.')
        return redirect('dashboard')
    
    # Logs de login
    login_logs = AuditLog.objects.filter(action='login').select_related('usuario').order_by('-created_at')
    
    # Estatísticas por usuário
    user_stats = User.objects.filter(ativo=True).annotate(
        total_logins=Count('audit_logs', filter=Q(audit_logs__action='login')),
        last_login_audit=Max('audit_logs__created_at', filter=Q(audit_logs__action='login'))
    ).order_by('-total_logins')
    
    # Paginação dos logs detalhados
    paginator = Paginator(login_logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_stats': user_stats,
    }
    
    return render(request, 'core/user_access_history.html', context)
