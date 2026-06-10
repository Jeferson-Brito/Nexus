from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json
from ..models import (
    Turno, AnalistaEscala, FolgaManual, EscalaRascunho, Department,
    IndicadorDesempenho, MetaMensalGlobal, SystemNotification,
    User, ModeloEscala, ConfiguracaoEscala
)



@login_required
def escala_view(request):
    """Página de Escala - Escala"""
    user = request.user
    if not user.is_administrador():
        if not (user.acesso_escala or user.acesso_ponto):
            messages.error(request, 'Você não tem permissão para acessar as ferramentas da Escala.')
            return redirect('dashboard')
    
    rascunho_id = request.GET.get('rascunho_id')
    rascunho_obj = None
    if rascunho_id:
        rascunho_obj = get_object_or_404(EscalaRascunho, id=rascunho_id)
        turnos = Turno.objects.filter(ativo=True, rascunho=rascunho_obj).order_by('ordem', 'nome')
        analistas = AnalistaEscala.objects.filter(ativo=True, rascunho=rascunho_obj).select_related('turno', 'modelo_escala').order_by('turno__ordem', 'ordem', 'nome')
        folgas = FolgaManual.objects.filter(rascunho=rascunho_obj).select_related('analista')
    else:
        # Carrega apenas operacional por padrÃ£o. A troca para gestÃ£o Ã© feita via JS/API.
        turnos = Turno.objects.filter(ativo=True, rascunho__isnull=True, escala_tipo='operacional').order_by('ordem', 'nome')
        analistas = AnalistaEscala.objects.filter(ativo=True, rascunho__isnull=True, escala_tipo='operacional').select_related('turno', 'modelo_escala').order_by('turno__ordem', 'ordem', 'nome')
        folgas = FolgaManual.objects.filter(rascunho__isnull=True, analista__escala_tipo='operacional').select_related('analista')
    
    turnos_data = [{
        'id': str(t.id),
        'nome': t.nome,
        'horario': t.horario,
        'cor': t.cor,
        'ordem': t.ordem,
        'min_analistas': t.min_analistas
    } for t in turnos]
    
    analistas_data = [{
        'id': str(a.id),
        'nome': a.nome,
        'turno': a.turno.nome if a.turno else None,
        'turno_id': a.turno.id if a.turno else None,
        'modelo_escala_id': a.modelo_escala.id if a.modelo_escala else None,
        'pausa': a.pausa,
        'data_primeira_folga': a.data_primeira_folga.isoformat() if a.data_primeira_folga else None,
        'ordem': a.ordem
    } for a in analistas]
    
    folgas_data = {}
    for f in folgas:
        key = f"{f.analista.id}-{f.data.year}-{f.data.month}-{f.data.day}"
        folgas_data[key] = {
            'id': f.id,
            'tipo': f.tipo,
            'motivo': f.motivo
        }
    
    # Ponto Eletrônico (antigo RH) vê a escala em modo somente-leitura se não tiver acesso de edição
    is_rh = user.acesso_ponto and not user.acesso_escala
    is_admin = (user.is_gestor() or user.is_administrador()) and not is_rh
    can_export = True  # Todos os usuÃ¡rios logados com acesso Ã  escala podem ver Resumo e Exportar
    
    is_planejamento_mode = request.resolver_match.url_name == 'planejamento_escala'
    is_config_mode = request.resolver_match.url_name == 'configuracao_escalas'

    # SeguranÃ§a: Apenas gestores e administradores acessam planejamento e configuraÃ§Ã£o
    if (is_planejamento_mode or is_config_mode) and not (user.is_gestor() or user.is_administrador()):
        messages.error(request, 'VocÃª nÃ£o tem permissÃ£o para acessar esta Ã¡rea da escala.')
        return redirect('escala')

    modelos = ModeloEscala.objects.all().order_by('nome')
    modelos_data = [{
        'id': m.id,
        'nome': m.nome,
        'dias_trabalhados': m.dias_trabalhados,
        'dias_folga': m.dias_folga,
        'tipo': m.tipo,
        'permite_fim_de_semana': m.permite_fim_de_semana,
        'observacao': m.observacao,
        'ciclo_personalizado': m.ciclo_personalizado
    } for m in modelos]
    
    config = ConfiguracaoEscala.objects.first()
    modelo_principal_id = config.modelo_escala_principal.id if config and config.modelo_escala_principal else None
    modelo_principal_id_gestao = config.modelo_escala_principal_gestao.id if config and config.modelo_escala_principal_gestao else None

    user_analista = None
    if user.is_authenticated:
        user_analista = AnalistaEscala.objects.filter(user=user, rascunho__isnull=True, ativo=True).first()

    has_operacional = Turno.objects.filter(escala_tipo='operacional').exists() or AnalistaEscala.objects.filter(escala_tipo='operacional').exists() or EscalaRascunho.objects.filter(escala_tipo='operacional').exists()
    has_gestao = Turno.objects.filter(escala_tipo='gestao').exists() or AnalistaEscala.objects.filter(escala_tipo='gestao').exists() or EscalaRascunho.objects.filter(escala_tipo='gestao').exists()

    context = {
        'turnos_json': json.dumps(turnos_data),
        'analistas_json': json.dumps(analistas_data),
        'folgas_json': json.dumps(folgas_data),
        'modelos_json': json.dumps(modelos_data),
        'modelo_principal_id': modelo_principal_id,
        'modelo_principal_id_gestao': modelo_principal_id_gestao,
        'has_operacional': has_operacional,
        'has_gestao': has_gestao,
        'is_admin': is_admin,
        'is_admin_json': 'true' if is_admin else 'false',
        'can_export': can_export,
        'is_rascunho': rascunho_obj is not None,
        'rascunho_id': str(rascunho_obj.id) if rascunho_obj else None,
        'rascunho_modelo_id': str(rascunho_obj.modelo_escala.id) if rascunho_obj and rascunho_obj.modelo_escala else None,
        'rascunho_nome': rascunho_obj.nome if rascunho_obj else None,
        'is_planejamento_mode': is_planejamento_mode,
        'is_config_mode': is_config_mode,
        'user_analista_id': str(user_analista.id) if user_analista else None,
    }
    
    return render(request, 'core/escala.html', context)



@login_required
def performance_view(request):
    """PÃ¡gina de Desempenho do Time"""
    user = request.user
    nrs_dept = Department.objects.filter(slug='escala').first()
    if not nrs_dept:
        nrs_dept = Department.objects.filter(name='Escala').first()
    if not nrs_dept and user.department:
        nrs_dept = user.department
    if not nrs_dept:
        nrs_dept = Department.objects.first()
    
    is_analista = user.role == 'analista'
    can_edit = user.role in ['gestor', 'administrador']
    page_title = "Meu Desempenho" if is_analista else "Desempenho do Time"

    if can_edit and nrs_dept:
        analistas = User.objects.filter(
            Q(department=nrs_dept) | 
            Q(indicadores_desempenho__department=nrs_dept)
        ).distinct().order_by('first_name', 'username')
    else:
        analistas = []
    
    selected_analista_id = request.GET.get('analista_id')
    if is_analista:
        selected_analista_id = user.id
    elif not selected_analista_id and analistas:
        selected_analista_id = analistas.first().id if analistas.exists() else None
    
    if selected_analista_id and str(selected_analista_id).isdigit():
        selected_analista_id = int(selected_analista_id)

    period = request.GET.get('period', '6')
    try:
        period_int = int(period) if period != 'all' else None
    except ValueError:
        period_int = 6

    kpis_data = []
    if selected_analista_id and nrs_dept:
        kpis_query = IndicadorDesempenho.objects.filter(
            analista_id=selected_analista_id,
            department=nrs_dept
        ).order_by('ano', 'mes')
        
        kpis = list(kpis_query)
        if period_int and len(kpis) > period_int:
            kpis = kpis[-period_int:]
        
        metas_globais = {
            f"{m.mes:02d}/{m.ano}": m 
            for m in MetaMensalGlobal.objects.filter(department=nrs_dept)
        }
        
        for kpi in kpis:
            label = f"{kpi.mes:02d}/{kpi.ano}"
            meta = metas_globais.get(label)
            kpis_data.append({
                'id': kpi.id,
                'mes': kpi.mes,
                'ano': kpi.ano,
                'label': label,
                'nps': float(kpi.nps) if kpi.nps else None,
                'tme': kpi.tme,
                'chats': kpi.chats,
                'meta_tme': meta.meta_tme if meta else None,
                'meta_nps': float(meta.meta_nps) if meta and meta.meta_nps else None,
                'meta_chats': meta.meta_chats if meta else None,
            })
    
    selected_analista = None
    if selected_analista_id:
        try:
            selected_analista = User.objects.get(id=selected_analista_id)
        except User.DoesNotExist:
            pass

    analistas_list = [{
        'id': a.id,
        'name': a.get_full_name() or a.username,
        'is_selected': a.id == selected_analista_id
    } for a in analistas]

    context = {
        'page_title': page_title,
        'is_analista': is_analista,
        'can_edit': can_edit,
        'can_edit_str': "true" if can_edit else "false",
        'analistas_list': analistas_list,
        'selected_analista_id': selected_analista_id,
        'selected_analista': selected_analista,
        'kpis_json': json.dumps(kpis_data),
        'current_period': period,
        'analistas_json': json.dumps([{
            'id': a.id,
            'nome': a.get_full_name() or a.username
        } for a in analistas]),
    }
    return render(request, 'core/desempenho.html', context)




@login_required
def auditoria_atendimentos_view(request):
    if not (request.user.is_gestor() or request.user.is_administrador() or request.user.is_analista()):
        return redirect('dashboard')
    dept = request.session.get('current_department_obj') or request.user.department
    return render(request, 'core/auditoria_atendimentos.html', {
        'title': 'Auditoria de Atendimentos', 'department': dept, 'is_admin': request.user.is_administrador(),
        'is_gestor': request.user.is_gestor(), 'is_analista': request.user.is_analista(),
    })

@login_required
def api_get_system_notifications(request):
    notifications = SystemNotification.objects.filter(is_active=True).order_by('-created_at')[:5]
    return JsonResponse({'notifications': [{
        'id': n.id, 'title': n.title, 'message': n.message, 'details': n.details,
        'category': n.get_category_display(), 'category_code': n.category,
        'created_at': n.created_at.strftime('%d/%m/%Y %H:%M'), 'timestamp': n.created_at.timestamp()
    } for n in notifications]})
