from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from ..models import IndicadorDesempenho, User, Department, MetaMensalGlobal


def get_nrs_department(user=None):
    """Obtém o departamento com fallback robusto (NRS Suporte -> Dept do Usuário -> Primeiro Dept) Ratio"""
    dept = Department.objects.filter(name='NRS Suporte').first()
    if not dept:
        dept = Department.objects.filter(slug='nrs-suporte').first()
    if not dept and user and hasattr(user, 'department') and user.department:
        dept = user.department
    if not dept:
        dept = Department.objects.first()
    return dept


@login_required
@require_http_methods(["GET"])
def api_kpis_list(request):
    """Lista KPIs - filtrado por analista se for um analista"""
    user = request.user
    
    # Obter departamento NRS Suporte
    try:
        nrs_dept = Department.objects.get(name='NRS Suporte')
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Departamento NRS Suporte não encontrado'}, status=404)
    
    # Filtrar analista específico (se solicitado)
    analista_id = request.GET.get('analista_id')
    
    if user.role == 'analista':
        # Analista só vê seus próprios KPIs
        kpis = IndicadorDesempenho.objects.filter(
            analista=user,
            department=nrs_dept
        ).order_by('ano', 'mes')
    elif analista_id:
        # Gestor/Admin filtrando por analista específico
        kpis = IndicadorDesempenho.objects.filter(
            analista_id=analista_id,
            department=nrs_dept
        ).order_by('ano', 'mes')
    else:
        # Gestor/Admin vê todos
        kpis = IndicadorDesempenho.objects.filter(
            department=nrs_dept
        ).order_by('ano', 'mes')
    
    data = [{
        'id': k.id,
        'analista_id': k.analista_id,
        'analista_nome': k.analista.get_full_name() or k.analista.username,
        'mes': k.mes,
        'ano': k.ano,
        'nps': float(k.nps) if k.nps else None,
        'tme': k.tme,
        'chats': k.chats,
    } for k in kpis]
    
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
def api_kpi_save(request):
    """Salvar ou atualizar KPI mensal"""
    user = request.user
    
    # Apenas gestor ou admin podem adicionar KPIs
    if user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    analista_id = data.get('analista_id')
    mes = data.get('mes')
    ano = data.get('ano')
    nps = data.get('nps')
    tme = data.get('tme')
    chats = data.get('chats', 0)
    
    # Campos de meta
    meta_tme = data.get('meta_tme')
    meta_nps = data.get('meta_nps')
    meta_chats = data.get('meta_chats')
    
    if not all([analista_id, mes, ano]):
        return JsonResponse({'error': 'Campos obrigatórios: analista_id, mes, ano'}, status=400)
    
    try:
        analista = User.objects.get(id=analista_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Analista não encontrado'}, status=404)
    
    # Obter departamento NRS Suporte
    try:
        nrs_dept = Department.objects.get(name='NRS Suporte')
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Departamento NRS Suporte não encontrado'}, status=404)
    
    # Criar ou atualizar
    kpi, created = IndicadorDesempenho.objects.update_or_create(
        analista=analista,
        mes=mes,
        ano=ano,
        department=nrs_dept,
        defaults={
            'nps': nps if nps is not None else None,
            'tme': tme if tme is not None else None,
            'chats': chats or 0,
            'meta_tme': meta_tme if meta_tme is not None else None,
            'meta_nps': meta_nps if meta_nps is not None else None,
            'meta_chats': meta_chats if meta_chats is not None else None,
        }
    )
    
    return JsonResponse({
        'id': kpi.id,
        'created': created,
        'message': 'KPI salvo com sucesso'
    })


@login_required
@require_http_methods(["DELETE"])
def api_kpi_delete(request, pk):
    """Excluir KPI"""
    user = request.user
    
    # Apenas gestor ou admin podem excluir KPIs
    if user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        kpi = IndicadorDesempenho.objects.get(id=pk)
        kpi.delete()
        return JsonResponse({'message': 'KPI excluído com sucesso'})
    except IndicadorDesempenho.DoesNotExist:
        return JsonResponse({'error': 'KPI não encontrado'}, status=404)


@login_required
@require_http_methods(["GET"])
def api_global_metas_list(request):
    """Lista todas as metas globais do departamento"""
    try:
        nrs_dept = Department.objects.get(name='NRS Suporte')
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Departamento não encontrado'}, status=404)
        
    metas = MetaMensalGlobal.objects.filter(department=nrs_dept).order_by('-ano', '-mes')
    data = [{
        'id': m.id,
        'mes': m.mes,
        'ano': m.ano,
        'label': f"{m.mes:02d}/{m.ano}",
        'meta_tme': m.meta_tme,
        'meta_nps': float(m.meta_nps) if m.meta_nps else None,
        'meta_chats': m.meta_chats,
    } for m in metas]
    
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
def api_global_meta_save(request):
    """Salva ou atualiza uma meta global"""
    user = request.user
    if user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
        
    try:
        data = json.loads(request.body)
        mes = data.get('mes')
        ano = data.get('ano')
        
        if not mes or not ano:
            return JsonResponse({'error': 'Mês e Ano são obrigatórios'}, status=400)
            
        # Obter departamento (prioridade: 'NRS Suporte', senão o do usuário, senão o primeiro disponível)
        nrs_dept = Department.objects.filter(name='NRS Suporte').first()
        if not nrs_dept and user.department:
            nrs_dept = user.department
        if not nrs_dept:
            nrs_dept = Department.objects.first()
            
        if not nrs_dept:
            return JsonResponse({'error': 'Nenhum departamento disponível'}, status=404)
            
        meta, created = MetaMensalGlobal.objects.update_or_create(
            mes=mes,
            ano=ano,
            department=nrs_dept,
            defaults={
                'meta_tme': data.get('meta_tme'),
                'meta_nps': data.get('meta_nps'),
                'meta_chats': data.get('meta_chats'),
            }
        )
        
        return JsonResponse({
            'success': True,
            'id': meta.id,
            'created': created
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_global_meta_delete(request, pk):
    """Exclui uma meta global"""
    user = request.user
    if user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
        
    try:
        meta = MetaMensalGlobal.objects.get(id=pk)
        meta.delete()
        return JsonResponse({'success': True, 'message': 'Meta global excluída'})
    except MetaMensalGlobal.DoesNotExist:
        return JsonResponse({'error': 'Meta não encontrada'}, status=404)


@login_required
@require_http_methods(["GET"])
def api_ranking(request):
    """Retorna ranking de analistas para um mês/ano específico"""
    user = request.user
    
    # Apenas gestores e admins podem ver o ranking
    if user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    # Verificar se é do departamento NRS Suporte
    try:
        nrs_dept = Department.objects.get(name='NRS Suporte')
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Departamento não encontrado'}, status=404)
    
    if user.department != nrs_dept and user.role != 'administrador':
        return JsonResponse({'error': 'Acesso restrito ao NRS Suporte'}, status=403)
    
    # Parâmetros
    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    
    if not mes or not ano:
        return JsonResponse({'error': 'Parâmetros mes e ano são obrigatórios'}, status=400)
    
    try:
        mes = int(mes)
        ano = int(ano)
    except ValueError:
        return JsonResponse({'error': 'Valores inválidos para mes/ano'}, status=400)
    
    # Buscar meta global do mês
    try:
        meta_global = MetaMensalGlobal.objects.get(department=nrs_dept, mes=mes, ano=ano)
        meta_tme = meta_global.meta_tme
        meta_nps = float(meta_global.meta_nps) if meta_global.meta_nps else None
        meta_chats = meta_global.meta_chats
    except MetaMensalGlobal.DoesNotExist:
        meta_tme = None
        meta_nps = None
        meta_chats = None
    
    # Buscar KPIs do mês
    kpis = IndicadorDesempenho.objects.filter(
        department=nrs_dept,
        mes=mes,
        ano=ano
    ).select_related('analista')
    
    ranking_data = []
    for kpi in kpis:
        # Calcular se atingiu cada meta
        tme_ok = None
        nps_ok = None
        chats_ok = None
        score = 0
        
        # TME: menor é melhor (≤ meta = OK)
        if kpi.tme is not None and meta_tme is not None:
            tme_ok = kpi.tme <= meta_tme
            if tme_ok:
                score += 1
        
        # NPS: maior é melhor (≥ meta = OK)
        kpi_nps = float(kpi.nps) if kpi.nps else None
        if kpi_nps is not None and meta_nps is not None:
            nps_ok = kpi_nps >= meta_nps
            if nps_ok:
                score += 1
        
        # Chats: maior é melhor (≥ meta = OK)
        if kpi.chats is not None and meta_chats is not None:
            chats_ok = kpi.chats >= meta_chats
            if chats_ok:
                score += 1
        
        ranking_data.append({
            'analista_id': kpi.analista_id,
            'analista_nome': kpi.analista.get_full_name() or kpi.analista.username,
            'tme': kpi.tme,
            'tme_ok': tme_ok,
            'nps': kpi_nps,
            'nps_ok': nps_ok,
            'chats': kpi.chats,
            'chats_ok': chats_ok,
            'score': score
        })
    
    # Ordenar: do melhor para o pior (maior score primeiro)
    ranking_data.sort(key=lambda x: (x['score'], x['nps'] or 0, -(x['tme'] or 9999)), reverse=True)
    
    # Adicionar posição
    for i, item in enumerate(ranking_data):
        item['posicao'] = i + 1
    
    return JsonResponse({
        'ranking': ranking_data,
        'meta_global': {
            'tme': meta_tme,
            'nps': meta_nps,
            'chats': meta_chats
        },
        'mes': mes,
        'ano': ano
    })


@login_required
@require_http_methods(["GET"])
def api_podium(request):
    """Retorna pódio (top 3) de analistas para cada métrica em um mês/ano específico"""
    # Pódio é visível para todos os usuários autenticados
    nrs_dept = get_nrs_department(request.user)
    if not nrs_dept:
        return JsonResponse({'error': 'Departamento não encontrado'}, status=404)
    
    # Parâmetros
    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    
    if not mes or not ano:
        return JsonResponse({'error': 'Parâmetros mes e ano são obrigatórios'}, status=400)
    
    try:
        mes = int(mes)
        ano = int(ano)
    except ValueError:
        return JsonResponse({'error': 'Valores inválidos para mes/ano'}, status=400)
    
    # Buscar KPIs do mês
    kpis = IndicadorDesempenho.objects.filter(
        department=nrs_dept,
        mes=mes,
        ano=ano
    ).select_related('analista')
    
    # Preparar dados para cada métrica
    tme_list = []
    nps_list = []
    chats_list = []
    
    for kpi in kpis:
        analista_nome = kpi.analista.get_full_name() or kpi.analista.username
        
        # TME: menor é melhor
        if kpi.tme is not None:
            tme_list.append({
                'analista_nome': analista_nome,
                'value': kpi.tme
            })
        
        # NPS: maior é melhor
        if kpi.nps is not None:
            nps_list.append({
                'analista_nome': analista_nome,
                'value': float(kpi.nps)
            })
        
        # Chats: maior é melhor
        if kpi.chats is not None:
            chats_list.append({
                'analista_nome': analista_nome,
                'value': kpi.chats
            })
    
    # Ordenar e pegar top 3
    # TME: menor é melhor (ordem crescente)
    tme_list.sort(key=lambda x: x['value'])
    tme_top3 = tme_list[:3]
    
    # NPS: maior é melhor (ordem decrescente)
    nps_list.sort(key=lambda x: x['value'], reverse=True)
    nps_top3 = nps_list[:3]
    
    # Chats: maior é melhor (ordem decrescente)
    chats_list.sort(key=lambda x: x['value'], reverse=True)
    chats_top3 = chats_list[:3]
    
    return JsonResponse({
        'tme_top3': tme_top3,
        'nps_top3': nps_top3,
        'chats_top3': chats_top3,
        'mes': mes,
        'ano': ano
    })
