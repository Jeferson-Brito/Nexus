"""
Views para gerenciamento da Base Nexus IA e Base de Auditoria IA
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Department

@login_required
def nexus_ia_base_view(request):
    """
    Renderiza a tela de gerenciamento da Base de Conhecimento do Nexus IA.
    Apenas Gestores e Administradores têm acesso.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, "Você não tem permissão para acessar esta área.")
        return redirect('dashboard')
        
    departments = Department.objects.all().order_by('name')
    
    context = {
        'departments': departments,
    }
    return render(request, 'core/nexus_ia_base.html', context)


@login_required
def base_auditoria_ia_view(request):
    """
    Renderiza a tela de gestão da Base de Conhecimento da IA Auditora.
    Apenas Gestores e Administradores têm acesso.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, "Você não tem permissão para acessar esta área.")
        return redirect('dashboard')

    context = {}
    return render(request, 'core/base_auditoria_ia.html', context)
