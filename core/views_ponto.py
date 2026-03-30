from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import RegistroPonto


@login_required
def ponto_kiosk(request):
    """
    Tela kiosk (tablet) para registro de ponto.
    Acesso permitido para role='tablet', gestores ou colaboradores com ponto_web_permitido.
    """
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    
    user = request.user
    role = getattr(user, 'role', '')
    colaborador = getattr(user, 'colaborador_perfil', None)
    
    is_tablet = role == 'tablet'
    is_staff = role in ('administrador', 'gestor')
    can_web_punch = colaborador and colaborador.ponto_web_permitido
    
    if not (is_tablet or is_staff or can_web_punch):
        logout(request)
        return redirect('login')
    
    colaborador_data = None
    if can_web_punch:
        from django.utils import timezone
        hoje = timezone.localtime().date()
        tipos_hoje = list(RegistroPonto.objects.filter(
            colaborador=colaborador, 
            data=hoje
        ).values_list('tipo', flat=True))
        
        colaborador_data = {
            'id': colaborador.id,
            'nome': colaborador.nome_completo,
            'cargo': colaborador.cargo_atual,
            'departamento': colaborador.department.name if colaborador.department else '',
            'foto_url': colaborador.foto.url if colaborador.foto else None,
            'tipos_hoje': tipos_hoje,
            'exigir_foto': colaborador.ponto_web_foto,
        }
    
    context = {
        'personal_punch': can_web_punch and not is_tablet and not is_staff,
        'colaborador_data': colaborador_data
    }
    
    return render(request, 'core/rh/ponto_kiosk.html', context)


@login_required
def ponto_admin(request):
    """
    Painel de gestão de ponto. Permite ver registros do dia,
    fazer lançamentos manuais rápidos e KPIs básicos.
    """
    role = getattr(request.user, 'role', '')
    if role not in ('administrador', 'gestor'):
        return render(request, 'core/403.html')
        
    return render(request, 'core/rh/ponto_admin.html')


@login_required
def ponto_relatorios(request):
    """
    Página de relatórios de ponto (mensal, exportações).
    """
    role = getattr(request.user, 'role', '')
    if role not in ('administrador', 'gestor'):
        return render(request, 'core/403.html')
        
    return render(request, 'core/rh/ponto_relatorios.html')
