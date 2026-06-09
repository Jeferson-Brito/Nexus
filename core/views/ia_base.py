"""
Views para gerenciamento da Base Brisoft IA e Base de Auditoria IA
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Department

@login_required
def configuracao_ia_view(request):
    """
    Painel Unificado de Configuração da IA e Sistema.
    Consolida: Base Brisoft IA, Base de Auditoria IA, Parâmetros e Exportação.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, "Você não tem permissão para acessar esta área.")
        return redirect('dashboard')

    departments = Department.objects.all().order_by('name')
    
    context = {
        'departments': departments,
    }
    return render(request, 'core/configuracao_ia.html', context)

