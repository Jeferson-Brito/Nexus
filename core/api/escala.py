from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from datetime import datetime

from ..models import Turno, AnalistaEscala, FolgaManual


from functools import wraps

def check_nrs_permission(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_administrador():
            # Permitir acesso se for NRS Suporte OU RH
            if not user.department or user.department.name not in ['NRS Suporte', 'RH']:
                return JsonResponse({'error': 'Acesso negado. Apenas departamentos NRS Suporte ou RH.'}, status=403)
            
            # Se for RH, permitir APENAS leitura
            if user.department.name == 'RH' and request.method not in ['GET']:
                return JsonResponse({'error': 'Acesso negado. RH possui apenas permissão de leitura.'}, status=403)
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ========================================
# API VIEWS PARA ESCALA NRS
# ========================================

@login_required
@check_nrs_permission
def api_turnos_list(request):
    """Lista todos os turnos"""
    turnos = Turno.objects.filter(ativo=True).order_by('ordem', 'nome')
    data = [{
        'id': str(t.id),
        'nome': t.nome,
        'horario': t.horario,
        'cor': t.cor,
        'ordem': t.ordem
    } for t in turnos]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_turno_create(request):
    """Cria um novo turno"""
    try:
        data = json.loads(request.body)
        turno = Turno.objects.create(
            nome=data.get('nome', ''),
            horario=data.get('horario', ''),
            cor=data.get('cor', '#2563eb'),
            ordem=data.get('ordem', 0)
        )
        return JsonResponse({
            'id': str(turno.id),
            'nome': turno.nome,
            'horario': turno.horario,
            'cor': turno.cor,
            'ordem': turno.ordem
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PUT", "DELETE"])
@check_nrs_permission
def api_turno_detail(request, pk):
    """Atualiza ou deleta um turno"""
    turno = get_object_or_404(Turno, pk=pk)
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            turno.nome = data.get('nome', turno.nome)
            turno.horario = data.get('horario', turno.horario)
            turno.cor = data.get('cor', turno.cor)
            turno.ordem = data.get('ordem', turno.ordem)
            turno.save()
            return JsonResponse({
                'id': str(turno.id),
                'nome': turno.nome,
                'horario': turno.horario,
                'cor': turno.cor,
                'ordem': turno.ordem
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        turno.ativo = False
        turno.save()
        return JsonResponse({'success': True})


@login_required
@check_nrs_permission
def api_analistas_list(request):
    """Lista todos os analistas da escala"""
    queryset = AnalistaEscala.objects.filter(ativo=True).select_related('turno')
    
    # Se for RH, filtrar apenas analistas que PERTENCEM ao NRS Suporte
    if not request.user.is_administrador() and request.user.department and request.user.department.name == 'RH':
        queryset = queryset.filter(user__department__name='NRS Suporte')
        
    analistas = queryset.order_by('turno__ordem', 'ordem', 'nome')
    data = [{
        'id': str(a.id),
        'nome': a.nome,
        'turno': a.turno.nome if a.turno else None,
        'turno_id': str(a.turno.id) if a.turno else None,
        'pausa': a.pausa,
        'data_primeira_folga': a.data_primeira_folga.isoformat() if a.data_primeira_folga else None,
        'ordem': a.ordem
    } for a in analistas]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_analista_create(request):
    """Cria um novo analista"""
    try:
        data = json.loads(request.body)
        turno = None
        if data.get('turno_id'):
            turno = Turno.objects.filter(id=data['turno_id']).first()
        elif data.get('turno'):
            turno = Turno.objects.filter(nome=data['turno']).first()
        
        data_folga = None
        if data.get('data_primeira_folga'):
            data_folga = datetime.strptime(data['data_primeira_folga'], '%Y-%m-%d').date()
        
        analista = AnalistaEscala.objects.create(
            nome=data.get('nome', ''),
            turno=turno,
            pausa=data.get('pausa', ''),
            data_primeira_folga=data_folga,
            ordem=data.get('ordem', 0)
        )
        return JsonResponse({
            'id': str(analista.id),
            'nome': analista.nome,
            'turno': analista.turno.nome if analista.turno else None,
            'turno_id': str(analista.turno.id) if analista.turno else None,
            'pausa': analista.pausa,
            'data_primeira_folga': analista.data_primeira_folga.isoformat() if analista.data_primeira_folga else None,
            'ordem': analista.ordem
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PUT", "DELETE"])
@check_nrs_permission
def api_analista_detail(request, pk):
    """Atualiza ou deleta um analista"""
    analista = get_object_or_404(AnalistaEscala, pk=pk)
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            analista.nome = data.get('nome', analista.nome)
            analista.pausa = data.get('pausa', analista.pausa)
            analista.ordem = data.get('ordem', analista.ordem)
            
            if data.get('turno_id'):
                analista.turno = Turno.objects.filter(id=data['turno_id']).first()
            elif data.get('turno'):
                analista.turno = Turno.objects.filter(nome=data['turno']).first()
            
            if data.get('data_primeira_folga'):
                analista.data_primeira_folga = datetime.strptime(data['data_primeira_folga'], '%Y-%m-%d').date()
            
            analista.save()
            return JsonResponse({
                'id': str(analista.id),
                'nome': analista.nome,
                'turno': analista.turno.nome if analista.turno else None,
                'turno_id': str(analista.turno.id) if analista.turno else None,
                'pausa': analista.pausa,
                'data_primeira_folga': analista.data_primeira_folga.isoformat() if analista.data_primeira_folga else None,
                'ordem': analista.ordem
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        analista.ativo = False
        analista.save()
        return JsonResponse({'success': True})


@login_required
@check_nrs_permission
def api_folgas_list(request):
    """Lista todas as folgas manuais"""
    queryset = FolgaManual.objects.select_related('analista')
    
    # Se for RH, filtrar apenas folgas de analistas que PERTENCEM ao NRS Suporte
    if not request.user.is_administrador() and request.user.department and request.user.department.name == 'RH':
        queryset = queryset.filter(analista__user__department__name='NRS Suporte')
        
    folgas = queryset.all()
    
    # Retornar como dicionário com chave no formato analista_id-ano-mes-dia
    data = {}
    for f in folgas:
        key = f"{f.analista.id}-{f.data.year}-{f.data.month}-{f.data.day}"
        data[key] = {
            'id': str(f.id),
            'tipo': f.tipo,
            'motivo': f.motivo
        }
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_folga_save(request):
    """Salva ou atualiza uma folga manual"""
    try:
        data = json.loads(request.body)
        analista = get_object_or_404(AnalistaEscala, pk=data['analista_id'])
        
        data_folga = datetime(
            int(data['ano']),
            int(data['mes']),
            int(data['dia'])
        ).date()
        
        folga, created = FolgaManual.objects.update_or_create(
            analista=analista,
            data=data_folga,
            defaults={
                'tipo': data.get('tipo', 'folga'),
                'motivo': data.get('motivo', '')
            }
        )
        
        return JsonResponse({
            'id': str(folga.id),
            'analista_id': str(analista.id),
            'data': folga.data.isoformat(),
            'tipo': folga.tipo,
            'motivo': folga.motivo,
            'created': created
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
@check_nrs_permission
def api_folga_delete(request, pk):
    """Deleta uma folga manual"""
    folga = get_object_or_404(FolgaManual, pk=pk)
    folga.delete()
    return JsonResponse({'success': True})
@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_turnos_reorder(request):
    """Reordena os turnos em massa"""
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        for index, turno_id in enumerate(ids):
            Turno.objects.filter(id=turno_id).update(ordem=index)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_analistas_reorder(request):
    """Reordena os analistas em massa"""
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        for index, analista_id in enumerate(ids):
            AnalistaEscala.objects.filter(id=analista_id).update(ordem=index)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_auditar_escala_ia(request):
    """Realiza a auditoria da escala usando IA"""
    try:
        data = json.loads(request.body)
        escala_summary = data.get('escala_summary', {})
        
        from ..services.ia_service import auditar_escala_ia
        
        resultado = auditar_escala_ia(escala_summary)
        
        return JsonResponse({
            'success': True,
            'analise': resultado.get('resposta', '')
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
