from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def ponto_kiosk(request):
    """
    Tela kiosk (tablet) para registro de ponto.
    Acesso permitido para role='tablet' ou admin/gestores que precisem testar.
    No kiosk, não há menu lateral nem barra superior.
    """
    # Se quiser forçar acesso apenas para tablet ou gestor, podemos checar
    role = getattr(request.user, 'role', '')
    if role not in ('tablet', 'administrador', 'gestor'):
        return render(request, 'core/403.html')  # Pode redirecionar para outro lugar
    
    return render(request, 'core/rh/ponto_kiosk.html')


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
