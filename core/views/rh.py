from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Colaborador, Department, Empresa, CentroCusto, Cargo, Holiday, Horario

@login_required
def rh_colaboradores_view(request):
    """Página de listagem geral de colaboradores (Cards)"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    
    return render(request, 'core/rh/colaboradores.html')

@login_required
def rh_colaborador_perfil_view(request, pk):
    """Página de perfil detalhado do colaborador (Dossiê)"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
        
    colaborador = get_object_or_404(Colaborador, pk=pk)
    departments_all = Department.objects.all().order_by('name')
    return render(request, 'core/rh/colaborador_perfil.html', {
        'colaborador': colaborador,
        'departments_all': departments_all,
    })

@login_required
def rh_cadastro_funcionario_view(request, pk=None):
    """Página de cadastro/edição de funcionário (full-page, estilo Control iD)"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
        
    colaborador = None
    colaborador_id = ''
    user_id = ''
    if pk:
        colaborador = get_object_or_404(
            Colaborador.objects.select_related('department', 'empresa', 'superior_direto'),
            pk=pk
        )
        colaborador_id = str(colaborador.pk)
    if request.GET.get('user_id'):
        user_id = request.GET.get('user_id')
    page_title = 'Editar Funcionário' if colaborador else 'Novo Funcionário'
    return render(request, 'core/rh/cadastro_funcionario.html', {
        'colaborador': colaborador,
        'colaborador_id': colaborador_id,
        'user_id': user_id,
        'page_title': page_title,
    })

UF_CHOICES = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
              'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']

@login_required
def rh_empresas_view(request):
    """Lista de empresas cadastradas"""
    return render(request, 'core/rh/empresas.html')

@login_required
def rh_cadastro_empresa_view(request, pk=None):
    """Cria ou edita uma empresa"""
    empresa = None
    empresa_id = ''
    if pk:
        empresa = get_object_or_404(Empresa, pk=pk)
        empresa_id = str(empresa.pk)
    page_title = 'Editar Empresa' if empresa else 'Nova Empresa'
    return render(request, 'core/rh/cadastro_empresa.html', {
        'empresa': empresa,
        'empresa_id': empresa_id,
        'page_title': page_title,
        'uf_choices': UF_CHOICES,
    })

@login_required
def rh_departamentos_view(request):
    """Tela de gestão de departamentos"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/departamentos_list.html')

@login_required
def rh_cargos_view(request):
    """Tela de gestão de cargos"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/cargos_list.html')

@login_required
def rh_centros_custo_view(request):
    """Tela de gestão de centros de custo"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/centros_custo_list.html')

@login_required
def rh_feriados_view(request):
    """Tela de gestão de feriados"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/feriados_list.html')

@login_required
def rh_atribuicoes_massa_view(request):
    """View para o wizard de atribuições em massa do RH"""
    user = request.user
    if not user.is_administrador():
        if not user.department or user.department.name != 'RH':
            messages.error(request, 'Acesso negado. Apenas o departamento de RH pode acessar esta funcionalidade.')
            return redirect('dashboard')

    context = {
        'title': 'Atribuições em Massa',
        'active_menu': 'rh_atribuicoes'
    }
    return render(request, 'core/rh/atribuicoes_massa.html', context)

@login_required
def rh_horarios_view(request):
    """Tela de listagem de horários"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/horarios_list.html')

@login_required
def rh_cadastro_horario_view(request, pk=None):
    """Página de cadastro/edição de horário"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
        
    horario = None
    horario_id = ''
    if pk:
        horario = get_object_or_404(Horario, pk=pk)
        horario_id = str(horario.pk)
        
    page_title = 'Editar Horário' if horario else 'Novo Horário'
    return render(request, 'core/rh/horarios_form.html', {
        'horario': horario,
        'horario_id': horario_id,
        'page_title': page_title,
    })

@login_required
def rh_apuracao_view(request):
    return render(request, 'core/rh/apuracao_ponto.html', {'page_title': 'Apuração de Ponto'})

@login_required
def rh_ponto_diario_view(request):
    """Página de apuração em lote por dia (Equipe)"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/ponto_diario.html', {'page_title': 'Ponto Diário'})

@login_required
def rh_inconsistencias_config_view(request):
    """Página de gestão de tipos de inconsistência"""
    if not request.user.is_administrador():
        messages.error(request, 'Acesso restrito para administradores.')
        return redirect('dashboard')
    return render(request, 'core/rh/config_inconsistencias.html', {'page_title': 'Tipos de Inconsistência'})

@login_required
def rh_inconsistencias_apuracao_view(request):
    """Página do Filtro de Inconsistências (Apuração)"""
    if not (request.user.is_gestor() or request.user.is_administrador() or getattr(request.user.department, 'name', '') == 'RH'):
        messages.error(request, 'Acesso restrito para Gestores ou Departamento de RH.')
        return redirect('dashboard')
    return render(request, 'core/rh/filtro_inconsistencias.html', {'page_title': 'Inconsistências'})
