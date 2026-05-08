from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from datetime import datetime

from ..models import Turno, AnalistaEscala, FolgaManual, EscalaRascunho, ModeloEscala, ConfiguracaoEscala, TrocaFolga
from django.utils import timezone
from django.contrib.auth import authenticate


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
# API VIEWS PARA MODELOS DE ESCALA
# ========================================
@login_required
@check_nrs_permission
def api_modelos_escala_list(request):
    """Lista todos os modelos de escala"""
    modelos = ModeloEscala.objects.all().order_by('nome')
    data = [{
        'id': str(m.id),
        'nome': m.nome,
        'dias_trabalhados': m.dias_trabalhados,
        'dias_folga': m.dias_folga,
        'tipo': m.tipo,
        'permite_fim_de_semana': m.permite_fim_de_semana,
        'observacao': m.observacao
    } for m in modelos]
    return JsonResponse(data, safe=False)

@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_modelo_escala_save(request):
    """Cria ou atualiza um modelo de escala"""
    try:
        data = json.loads(request.body)
        modelo_id = data.get('id')
        
        # Validação 6x1 não pode ser rotativa
        if int(data.get('dias_trabalhados', 5)) == 6 and int(data.get('dias_folga', 1)) == 1 and data.get('tipo') == 'rotativa':
            return JsonResponse({'error': 'Escalas 6x1 não podem ser rotativas devido a regras de descanso semanal.'}, status=400)

        if modelo_id:
            modelo = get_object_or_404(ModeloEscala, pk=modelo_id)
            modelo.nome = data.get('nome', modelo.nome)
            modelo.dias_trabalhados = data.get('dias_trabalhados', modelo.dias_trabalhados)
            modelo.dias_folga = data.get('dias_folga', modelo.dias_folga)
            modelo.tipo = data.get('tipo', modelo.tipo)
            modelo.permite_fim_de_semana = data.get('permite_fim_de_semana', modelo.permite_fim_de_semana)
            modelo.observacao = data.get('observacao', modelo.observacao)
            modelo.save()
        else:
            modelo = ModeloEscala.objects.create(
                nome=data.get('nome', ''),
                dias_trabalhados=data.get('dias_trabalhados', 5),
                dias_folga=data.get('dias_folga', 2),
                tipo=data.get('tipo', 'fixa'),
                permite_fim_de_semana=data.get('permite_fim_de_semana', True),
                observacao=data.get('observacao', '')
            )
            
        return JsonResponse({
            'success': True, 
            'id': str(modelo.id),
            'nome': modelo.nome,
            'dias_trabalhados': modelo.dias_trabalhados,
            'dias_folga': modelo.dias_folga,
            'tipo': modelo.tipo,
            'permite_fim_de_semana': modelo.permite_fim_de_semana,
            'observacao': modelo.observacao
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["DELETE"])
@check_nrs_permission
def api_modelo_escala_delete(request, pk):
    """Exclui um modelo de escala"""
    modelo = get_object_or_404(ModeloEscala, pk=pk)
    # Check if it is being used
    if modelo.rascunhos.exists() or modelo.analistas.exists() or ConfiguracaoEscala.objects.filter(modelo_escala_principal=modelo).exists():
        return JsonResponse({'error': 'Não é possível excluir um modelo que está em uso por uma escala ou analista.'}, status=400)
    
    modelo.delete()
    return JsonResponse({'success': True})

# ========================================
# API VIEWS PARA ESCALA NRS
# ========================================

@login_required
@check_nrs_permission
def api_turnos_list(request):
    """Lista todos os turnos"""
    rascunho_id = request.GET.get('rascunho_id')
    if rascunho_id:
        turnos = Turno.objects.filter(ativo=True, rascunho_id=rascunho_id).order_by('ordem', 'nome')
    else:
        turnos = Turno.objects.filter(ativo=True, rascunho__isnull=True).order_by('ordem', 'nome')
        
    data = [{
        'id': str(t.id),
        'nome': t.nome,
        'horario': t.horario,
        'cor': t.cor,
        'ordem': t.ordem,
        'min_analistas': t.min_analistas,
    } for t in turnos]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_turno_create(request):
    """Cria um novo turno"""
    try:
        data = json.loads(request.body)
        rascunho_id = data.get('rascunho_id')
        rascunho = EscalaRascunho.objects.get(id=rascunho_id) if rascunho_id else None
        
        turno = Turno.objects.create(
            nome=data.get('nome', ''),
            horario=data.get('horario', ''),
            cor=data.get('cor', '#2563eb'),
            ordem=data.get('ordem', 0),
            min_analistas=int(data.get('min_analistas', 0)),
            rascunho=rascunho
        )
        return JsonResponse({
            'id': str(turno.id),
            'nome': turno.nome,
            'horario': turno.horario,
            'cor': turno.cor,
            'ordem': turno.ordem,
            'min_analistas': turno.min_analistas,
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
            turno.min_analistas = int(data.get('min_analistas', turno.min_analistas))
            turno.save()
            return JsonResponse({
                'id': str(turno.id),
                'nome': turno.nome,
                'horario': turno.horario,
                'cor': turno.cor,
                'ordem': turno.ordem,
                'min_analistas': turno.min_analistas,
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
    rascunho_id = request.GET.get('rascunho_id')
    if rascunho_id:
        queryset = AnalistaEscala.objects.filter(ativo=True, rascunho_id=rascunho_id).select_related('turno')
    else:
        queryset = AnalistaEscala.objects.filter(ativo=True, rascunho__isnull=True).select_related('turno')
    
    # Se for RH, filtrar apenas analistas que PERTENCEM ao NRS Suporte
    if not request.user.is_administrador() and request.user.department and request.user.department.name == 'RH':
        queryset = queryset.filter(user__department__name='NRS Suporte')
        
    analistas = queryset.order_by('turno__ordem', 'ordem', 'nome')
    data = [{
        'id': str(a.id),
        'nome': a.nome,
        'turno': a.turno.nome if a.turno else None,
        'turno_id': str(a.turno.id) if a.turno else None,
        'modelo_escala_id': str(a.modelo_escala.id) if a.modelo_escala else None,
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
        rascunho_id = data.get('rascunho_id')
        rascunho = EscalaRascunho.objects.get(id=rascunho_id) if rascunho_id else None
        
        turno = None
        if data.get('turno_id'):
            turno = Turno.objects.filter(id=data['turno_id']).first()
        elif data.get('turno'):
            turno = Turno.objects.filter(nome=data['turno']).first()
        
        data_folga = None
        if data.get('data_primeira_folga'):
            data_folga = datetime.strptime(data['data_primeira_folga'], '%Y-%m-%d').date()
        
        modelo_escala = None
        if data.get('modelo_escala_id'):
            modelo_escala = ModeloEscala.objects.filter(id=data['modelo_escala_id']).first()

        analista = AnalistaEscala.objects.create(
            nome=data.get('nome', ''),
            turno=turno,
            modelo_escala=modelo_escala,
            pausa=data.get('pausa', ''),
            data_primeira_folga=data_folga,
            ordem=data.get('ordem', 0),
            rascunho=rascunho
        )
        return JsonResponse({
            'id': str(analista.id),
            'nome': analista.nome,
            'turno': analista.turno.nome if analista.turno else None,
            'turno_id': str(analista.turno.id) if analista.turno else None,
            'modelo_escala_id': str(analista.modelo_escala.id) if analista.modelo_escala else None,
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
            
            if 'modelo_escala_id' in data:
                if data['modelo_escala_id']:
                    analista.modelo_escala = ModeloEscala.objects.filter(id=data['modelo_escala_id']).first()
                else:
                    analista.modelo_escala = None
            
            if data.get('data_primeira_folga'):
                analista.data_primeira_folga = datetime.strptime(data['data_primeira_folga'], '%Y-%m-%d').date()
            
            analista.save()
            return JsonResponse({
                'id': str(analista.id),
                'nome': analista.nome,
                'turno': analista.turno.nome if analista.turno else None,
                'turno_id': str(analista.turno.id) if analista.turno else None,
                'modelo_escala_id': str(analista.modelo_escala.id) if analista.modelo_escala else None,
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
    rascunho_id = request.GET.get('rascunho_id')
    if rascunho_id:
        queryset = FolgaManual.objects.filter(rascunho_id=rascunho_id).select_related('analista')
    else:
        queryset = FolgaManual.objects.filter(rascunho__isnull=True).select_related('analista')
    
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
        rascunho_id = data.get('rascunho_id')
        rascunho = EscalaRascunho.objects.get(id=rascunho_id) if rascunho_id else None
        
        data_folga = datetime(
            int(data['ano']),
            int(data['mes']),
            int(data['dia'])
        ).date()
        
        # Filtramos por rascunho também
        folga = FolgaManual.objects.filter(analista=analista, data=data_folga, rascunho=rascunho).first()
        if folga:
            folga.tipo = data.get('tipo', 'folga')
            folga.motivo = data.get('motivo', '')
            folga.save()
            created = False
        else:
            folga = FolgaManual.objects.create(
                analista=analista,
                data=data_folga,
                rascunho=rascunho,
                tipo=data.get('tipo', 'folga'),
                motivo=data.get('motivo', '')
            )
            created = True
        
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

# ========================================
# API VIEWS PARA RASCUNHOS DE ESCALA
# ========================================

@login_required
@check_nrs_permission
def api_rascunhos_list(request):
    """Lista os rascunhos do usuário/sistema"""
    rascunhos = EscalaRascunho.objects.all().order_by('-updated_at')
    data = [{
        'id': r.id,
        'nome': r.nome,
        'autor': r.autor.get_full_name() or r.autor.username,
        'data_atualizacao': r.updated_at.strftime('%d/%m/%Y %H:%M')
    } for r in rascunhos]
    return JsonResponse(data, safe=False)

@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_rascunho_create(request):
    """Cria um novo rascunho: em branco (sem turnos, analistas sem turno) ou cópia de uma fonte."""
    try:
        if EscalaRascunho.objects.count() >= 3:
            return JsonResponse({'error': 'Limite de 3 rascunhos atingido. Exclua um rascunho para criar outro.'}, status=400)

        data = json.loads(request.body)
        nome = data.get('nome', f'Rascunho {datetime.now().strftime("%d/%m %H:%M")}')
        tipo = data.get('tipo', 'copia')        # 'em_branco' ou 'copia'
        fonte_id = data.get('fonte_id', 'principal')  # 'principal' ou ID numérico de um rascunho
        modelo_escala_id = data.get('modelo_escala_id')

        modelo_escala = None
        if modelo_escala_id:
            modelo_escala = get_object_or_404(ModeloEscala, pk=modelo_escala_id)

        rascunho = EscalaRascunho.objects.create(nome=nome, autor=request.user, modelo_escala=modelo_escala)

        if tipo == 'em_branco':
            # --- MODO EM BRANCO ---
            # Sem turnos, sem folgas. Apenas copia os analistas da escala principal
            # sem vínculo de turno, para que possam ser atribuídos manualmente depois.
            analistas_ativos = AnalistaEscala.objects.filter(ativo=True, rascunho__isnull=True)
            for a in analistas_ativos:
                AnalistaEscala.objects.create(
                    rascunho=rascunho,
                    user=a.user,
                    nome=a.nome,
                    turno=None,          # Sem turno - será definido na simulação
                    pausa='',
                    data_primeira_folga=None,
                    ordem=a.ordem,
                    ativo=a.ativo
                )

        else:
            # --- MODO CÓPIA ---
            # Determinar a fonte: escala principal ou um rascunho existente
            if fonte_id == 'principal' or not fonte_id:
                turnos_fonte = Turno.objects.filter(ativo=True, rascunho__isnull=True)
                analistas_fonte = AnalistaEscala.objects.filter(ativo=True, rascunho__isnull=True)
                folgas_fonte = FolgaManual.objects.filter(rascunho__isnull=True)
            else:
                fonte_rascunho = get_object_or_404(EscalaRascunho, pk=fonte_id)
                turnos_fonte = Turno.objects.filter(ativo=True, rascunho=fonte_rascunho)
                analistas_fonte = AnalistaEscala.objects.filter(ativo=True, rascunho=fonte_rascunho)
                folgas_fonte = FolgaManual.objects.filter(rascunho=fonte_rascunho)

            # Copiar Turnos
            turno_map = {}
            for t in turnos_fonte:
                novo_t = Turno.objects.create(
                    rascunho=rascunho,
                    nome=t.nome,
                    horario=t.horario,
                    cor=t.cor,
                    ordem=t.ordem,
                    ativo=t.ativo
                )
                turno_map[t.id] = novo_t

            # Copiar Analistas
            analista_map = {}
            for a in analistas_fonte:
                novo_turno = turno_map.get(a.turno_id) if a.turno_id else None
                novo_a = AnalistaEscala.objects.create(
                    rascunho=rascunho,
                    user=a.user,
                    nome=a.nome,
                    turno=novo_turno,
                    pausa=a.pausa,
                    data_primeira_folga=a.data_primeira_folga,
                    ordem=a.ordem,
                    ativo=a.ativo
                )
                analista_map[a.id] = novo_a

            # Copiar Folgas
            for f in folgas_fonte:
                if f.analista_id in analista_map:
                    FolgaManual.objects.create(
                        rascunho=rascunho,
                        analista=analista_map[f.analista_id],
                        data=f.data,
                        tipo=f.tipo,
                        motivo=f.motivo
                    )

        return JsonResponse({'success': True, 'id': rascunho.id, 'nome': rascunho.nome})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_rascunho_copiar_turnos(request, pk):
    """Copia turnos e analistas de uma escala fonte para o rascunho atual"""
    try:
        rascunho_destino = get_object_or_404(EscalaRascunho, pk=pk)
        data = json.loads(request.body)
        fonte_id = data.get('fonte_id', 'principal')

        if fonte_id == 'principal' or not fonte_id:
            turnos_fonte = Turno.objects.filter(ativo=True, rascunho__isnull=True)
            analistas_fonte = AnalistaEscala.objects.filter(ativo=True, rascunho__isnull=True)
        else:
            fonte_rascunho = get_object_or_404(EscalaRascunho, pk=fonte_id)
            turnos_fonte = Turno.objects.filter(ativo=True, rascunho=fonte_rascunho)
            analistas_fonte = AnalistaEscala.objects.filter(ativo=True, rascunho=fonte_rascunho)

        if not turnos_fonte.exists():
            return JsonResponse({'error': 'A escala fonte não possui turnos para copiar.'}, status=400)

        # Mapeamento para associar analistas aos novos turnos (por ID e por NOME)
        mapa_turnos_id = {}
        mapa_turnos_nome = {}
        
        turnos_criados = []
        for t in turnos_fonte:
            # Tenta encontrar turno existente com mesmo nome no destino para não duplicar se já existir
            novo_t = Turno.objects.filter(rascunho=rascunho_destino, nome=t.nome).first()
            if not novo_t:
                novo_t = Turno.objects.create(
                    rascunho=rascunho_destino,
                    nome=t.nome,
                    horario=t.horario,
                    cor=t.cor,
                    ordem=t.ordem,
                    ativo=t.ativo
                )
            
            mapa_turnos_id[t.id] = novo_t
            mapa_turnos_nome[t.nome] = novo_t
            
            turnos_criados.append({
                'id': novo_t.id,
                'nome': novo_t.nome,
                'horario': novo_t.horario,
                'cor': novo_t.cor
            })

        # Copiar/Atualizar Analistas
        for a in analistas_fonte:
            novo_turno = mapa_turnos_id.get(a.turno_id) if a.turno else None
            
            # Tenta encontrar analista existente no destino pelo nome
            analista_destino = AnalistaEscala.objects.filter(rascunho=rascunho_destino, nome=a.nome).first()
            
            if analista_destino:
                # Atualiza analista existente
                analista_destino.turno = novo_turno
                analista_destino.user = a.user
                analista_destino.modelo_escala = a.modelo_escala
                analista_destino.pausa = a.pausa
                analista_destino.data_primeira_folga = a.data_primeira_folga
                analista_destino.ordem = a.ordem
                analista_destino.ativo = a.ativo
                analista_destino.save()
            else:
                # Cria novo analista
                AnalistaEscala.objects.create(
                    rascunho=rascunho_destino,
                    user=a.user,
                    nome=a.nome,
                    turno=novo_turno,
                    modelo_escala=a.modelo_escala,
                    pausa=a.pausa,
                    data_primeira_folga=a.data_primeira_folga,
                    ordem=a.ordem,
                    ativo=a.ativo
                )

        return JsonResponse({'success': True, 'turnos': turnos_criados})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["DELETE"])
@check_nrs_permission
def api_rascunho_delete(request, pk):
    """Exclui um rascunho"""
    rascunho = get_object_or_404(EscalaRascunho, pk=pk)
    rascunho.delete()
    return JsonResponse({'success': True})

@login_required
@require_http_methods(["POST"])
@check_nrs_permission
def api_rascunho_publish(request, pk):
    """Substitui a escala principal pelo rascunho, exigindo senha de admin"""
    try:
        data = json.loads(request.body)
        password = data.get('password')
        
        if not request.user.is_administrador():
            return JsonResponse({'error': 'Apenas administradores podem substituir a escala principal.'}, status=403)
            
        if not request.user.check_password(password):
            return JsonResponse({'error': 'Senha incorreta.'}, status=403)
            
        rascunho = get_object_or_404(EscalaRascunho, pk=pk)
        
        # Excluir escala principal atual
        Turno.objects.filter(rascunho__isnull=True).delete()
        AnalistaEscala.objects.filter(rascunho__isnull=True).delete()
        FolgaManual.objects.filter(rascunho__isnull=True).delete()
        
        # Promover rascunho para principal
        Turno.objects.filter(rascunho=rascunho).update(rascunho=None)
        AnalistaEscala.objects.filter(rascunho=rascunho).update(rascunho=None)
        FolgaManual.objects.filter(rascunho=rascunho).update(rascunho=None)

        # Salvar o modelo_escala do rascunho na configuração principal
        config, created = ConfiguracaoEscala.objects.get_or_create(id=1)
        config.modelo_escala_principal = rascunho.modelo_escala
        config.save()
        
        # Excluir o objeto rascunho (que agora está vazio)
        rascunho.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ========================================
# API VIEWS PARA TROCAS DE FOLGA
# ========================================

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE COBERTURA DE TURNO
# ─────────────────────────────────────────────────────────────────────────────

from datetime import date as date_type, timedelta

def _get_modelo_ciclo(analista):
    """Retorna (dias_trabalhados, dias_folga) do modelo do analista."""
    modelo = analista.modelo_escala
    if not modelo:
        return (6, 2)  # Padrão 6x2
    return (modelo.dias_trabalhados, modelo.dias_folga)


def calcular_analistas_ativos(turno, data_alvo, rascunho=None):
    """
    Dado um turno e uma data, retorna o número de analistas que estarão
    TRABALHANDO naquele dia (excluindo os que estão de folga manual ou cíclica).
    """
    if rascunho:
        analistas = AnalistaEscala.objects.filter(turno=turno, ativo=True, rascunho=rascunho)
    else:
        analistas = AnalistaEscala.objects.filter(turno=turno, ativo=True, rascunho__isnull=True)

    ativos = 0
    for analista in analistas:
        # 1. Verificar folga manual explícita
        folga_manual = FolgaManual.objects.filter(
            analista=analista, data=data_alvo, rascunho=rascunho
        ).first()
        if folga_manual:
            if folga_manual.tipo != 'trabalho':
                continue  # Está de folga/férias/atestado
            else:
                ativos += 1
                continue

        # 2. Calcular pelo ciclo
        trab, folga = _get_modelo_ciclo(analista)
        ciclo_total = trab + folga

        primeira_folga = analista.data_primeira_folga
        if not primeira_folga:
            ativos += 1
            continue

        data_alvo_norm = data_alvo if isinstance(data_alvo, date_type) else data_alvo.date()
        diff_days = (data_alvo_norm - primeira_folga).days
        pos = ((diff_days % ciclo_total) + ciclo_total) % ciclo_total

        if pos < folga:
            continue  # Dia de folga cíclica
        ativos += 1

    return ativos


def validar_regras_troca(solicitante, receptor, data_solicitante, data_receptor, tipo, rascunho=None):
    """
    Verifica se a troca deixaria algum turno abaixo do mínimo de analistas.
    Retorna (True, None) se válida ou (False, mensagem_de_erro) se inválida.
    """
    # Converter strings de data para date se necessário
    if isinstance(data_solicitante, str):
        data_solicitante = datetime.strptime(data_solicitante, '%Y-%m-%d').date()
    if data_receptor and isinstance(data_receptor, str):
        data_receptor = datetime.strptime(data_receptor, '%Y-%m-%d').date()

    def checar_saida(analista, data_saida):
        """Verifica se o turno do analista ficará abaixo do mínimo quando ele sair naquele dia."""
        turno = analista.turno
        if not turno or turno.min_analistas <= 0:
            return True, None
        ativos_atuais = calcular_analistas_ativos(turno, data_saida, rascunho)
        # Após a troca, este analista vai sair do turno nesse dia, então -1
        ativos_pos_troca = ativos_atuais - 1
        if ativos_pos_troca < turno.min_analistas:
            return False, (
                f"Cobertura insuficiente: o turno '{turno.nome}' em {data_saida.strftime('%d/%m/%Y')} "
                f"ficaria com apenas {ativos_pos_troca} analista(s) ativo(s), "
                f"abaixo do mínimo exigido de {turno.min_analistas}."
            )
        return True, None

    # Cenário 1 (folga própria): solicitante sai no dia atual e entra no dia desejado
    # Cenário 2 (troca mútua): solicitante sai no dia atual, receptor sai no seu dia

    # Verificar saída do solicitante do seu dia de folga (ele vai trabalhar nesse dia)
    ok, msg = checar_saida(solicitante, data_solicitante)
    if not ok:
        return False, msg

    # Verificar saída do receptor do seu dia (apenas para troca entre analistas)
    if tipo == 'analista' and receptor and data_receptor:
        ok, msg = checar_saida(receptor, data_receptor)
        if not ok:
            return False, msg

    return True, None


def _serializar_troca(t):
    """Serializa um objeto TrocaFolga para dict JSON."""
    return {
        'id': t.id,
        'tipo': t.tipo,
        'tipo_display': t.get_tipo_display(),
        'status': t.status,
        'status_display': t.get_status_display(),
        'solicitante_id': t.solicitante.id,
        'solicitante_nome': t.solicitante.nome,
        'receptor_id': t.receptor.id if t.receptor else None,
        'receptor_nome': t.receptor.nome if t.receptor else None,
        'data_solicitante': t.data_solicitante.isoformat(),
        'data_receptor': t.data_receptor.isoformat() if t.data_receptor else None,
        'motivo': t.motivo,
        'motivo_rejeicao': t.motivo_rejeicao,
        'aprovado_gestor_por': t.aprovado_gestor_por.get_full_name() or t.aprovado_gestor_por.username if t.aprovado_gestor_por else None,
        'aprovado_gestor_em': t.aprovado_gestor_em.isoformat() if t.aprovado_gestor_em else None,
        'aprovado_receptor_em': t.aprovado_receptor_em.isoformat() if t.aprovado_receptor_em else None,
        'created_at': t.created_at.isoformat(),
        'rascunho_id': t.rascunho_id,
    }


@login_required
def api_trocas_list(request):
    """Lista trocas de folga. Filtra por status e rascunho. Analistas veem apenas as suas."""
    rascunho_id = request.GET.get('rascunho_id')
    status_filter = request.GET.get('status')  # Ex: 'pendente_gestor'

    if rascunho_id:
        qs = TrocaFolga.objects.filter(rascunho_id=rascunho_id)
    else:
        qs = TrocaFolga.objects.filter(rascunho__isnull=True)

    # Analistas veem apenas trocas onde são solicitante ou receptor
    if not request.user.is_administrador() and request.user.role == 'analista':
        analista_perfis = AnalistaEscala.objects.filter(user=request.user).values_list('id', flat=True)
        qs = qs.filter(
            solicitante_id__in=analista_perfis
        ) | qs.filter(
            receptor_id__in=analista_perfis
        )
        qs = qs.distinct()

    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.select_related('solicitante', 'receptor', 'aprovado_gestor_por').order_by('-created_at')
    return JsonResponse([_serializar_troca(t) for t in qs], safe=False)


@login_required
@require_http_methods(['POST'])
def api_troca_create(request):
    """Cria uma nova solicitação de troca de folga."""
    try:
        data = json.loads(request.body)
        tipo = data.get('tipo')  # 'propria' ou 'analista'
        solicitante_id = data.get('solicitante_id')
        data_solicitante = data.get('data_solicitante')
        data_receptor = data.get('data_receptor')
        receptor_id = data.get('receptor_id')
        motivo = data.get('motivo', '')
        rascunho_id = data.get('rascunho_id')

        if not all([tipo, solicitante_id, data_solicitante]):
            return JsonResponse({'error': 'Campos obrigatórios: tipo, solicitante_id, data_solicitante.'}, status=400)

        solicitante = get_object_or_404(AnalistaEscala, pk=solicitante_id)
        rascunho = EscalaRascunho.objects.get(id=rascunho_id) if rascunho_id else None

        receptor = None
        if tipo == 'analista':
            if not receptor_id or not data_receptor:
                return JsonResponse({'error': 'Cenário 2 requer receptor_id e data_receptor.'}, status=400)
            receptor = get_object_or_404(AnalistaEscala, pk=receptor_id)

        # Verificar que não há outra troca pendente para os mesmos dados
        conflito = TrocaFolga.objects.filter(
            solicitante=solicitante,
            data_solicitante=data_solicitante,
            status__in=['pendente_analista', 'pendente_gestor']
        ).first()
        if conflito:
            return JsonResponse({'error': 'Já existe uma solicitação pendente para esta folga.'}, status=400)

        # Validar regras de cobertura mínima de turno
        ok, motivo = validar_regras_troca(
            solicitante=solicitante,
            receptor=receptor,
            data_solicitante=data_solicitante,
            data_receptor=data_receptor,
            tipo=tipo,
            rascunho=rascunho
        )
        if not ok:
            return JsonResponse({'error': motivo, 'tipo': 'cobertura_insuficiente'}, status=400)

        status_inicial = 'pendente_analista' if tipo == 'analista' else 'pendente_gestor'

        troca = TrocaFolga.objects.create(
            tipo=tipo,
            solicitante=solicitante,
            receptor=receptor,
            data_solicitante=datetime.strptime(data_solicitante, '%Y-%m-%d').date(),
            data_receptor=datetime.strptime(data_receptor, '%Y-%m-%d').date() if data_receptor else None,
            motivo=motivo,
            status=status_inicial,
            rascunho=rascunho,
        )
        return JsonResponse({'success': True, 'troca': _serializar_troca(troca)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
def api_troca_aprovar_analista(request, pk):
    """Receptor aprova a troca (Cenário 2). Move status para pendente_gestor."""
    try:
        troca = get_object_or_404(TrocaFolga, pk=pk)
        if troca.status != 'pendente_analista':
            return JsonResponse({'error': 'Esta troca não está aguardando aprovação do analista.'}, status=400)
        troca.status = 'pendente_gestor'
        troca.aprovado_receptor_em = timezone.now()
        troca.save()
        return JsonResponse({'success': True, 'troca': _serializar_troca(troca)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
def api_troca_rejeitar_analista(request, pk):
    """Receptor rejeita a troca (Cenário 2)."""
    try:
        troca = get_object_or_404(TrocaFolga, pk=pk)
        if troca.status != 'pendente_analista':
            return JsonResponse({'error': 'Esta troca não está aguardando aprovação do analista.'}, status=400)
        data = json.loads(request.body)
        troca.status = 'rejeitada'
        troca.motivo_rejeicao = data.get('motivo_rejeicao', 'Recusado pelo analista.')
        troca.save()
        return JsonResponse({'success': True, 'troca': _serializar_troca(troca)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
@check_nrs_permission
def api_troca_aprovar_gestor(request, pk):
    """Gestor/admin aprova e aplica a troca na escala."""
    try:
        troca = get_object_or_404(TrocaFolga, pk=pk)
        if troca.status != 'pendente_gestor':
            return JsonResponse({'error': 'Esta troca não está aguardando aprovação do gestor.'}, status=400)

        rascunho = troca.rascunho

        # Re-validar regras de cobertura mínima no momento da aprovação final
        ok, motivo = validar_regras_troca(
            solicitante=troca.solicitante,
            receptor=troca.receptor,
            data_solicitante=troca.data_solicitante,
            data_receptor=troca.data_receptor,
            tipo=troca.tipo,
            rascunho=rascunho
        )
        if not ok:
            return JsonResponse({'error': motivo, 'tipo': 'cobertura_insuficiente'}, status=400)

        def _aplicar_folga(analista, data_trabalho, data_folga):
            """Remove folga no dia de trabalho e insere folga no novo dia."""
            # Remover qualquer registro manual que force 'folga' no dia de trabalho
            FolgaManual.objects.filter(analista=analista, data=data_trabalho, rascunho=rascunho).delete()
            # Criar/atualizar folga manual no novo dia
            FolgaManual.objects.update_or_create(
                analista=analista,
                data=data_folga,
                rascunho=rascunho,
                defaults={'tipo': 'folga', 'motivo': f'Troca de folga aprovada (ID #{troca.id})'}
            )
            # Garantir que o dia cedido é marcado como trabalho (caso fosse folga automática)
            FolgaManual.objects.update_or_create(
                analista=analista,
                data=data_trabalho,
                rascunho=rascunho,
                defaults={'tipo': 'trabalho', 'motivo': f'Troca de folga aprovada (ID #{troca.id})'}
            )

        if troca.tipo == 'propria':
            # Cenário 1: mover folga do solicitante
            _aplicar_folga(troca.solicitante, troca.data_solicitante, troca.data_receptor)
        else:
            # Cenário 2: troca mútua
            _aplicar_folga(troca.solicitante, troca.data_solicitante, troca.data_receptor)
            _aplicar_folga(troca.receptor, troca.data_receptor, troca.data_solicitante)

        troca.status = 'aprovada'
        troca.aprovado_gestor_por = request.user
        troca.aprovado_gestor_em = timezone.now()
        troca.save()
        return JsonResponse({'success': True, 'troca': _serializar_troca(troca)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
@check_nrs_permission
def api_troca_rejeitar_gestor(request, pk):
    """Gestor/admin rejeita a troca."""
    try:
        troca = get_object_or_404(TrocaFolga, pk=pk)
        if troca.status != 'pendente_gestor':
            return JsonResponse({'error': 'Esta troca não está aguardando aprovação do gestor.'}, status=400)
        data = json.loads(request.body)
        troca.status = 'rejeitada'
        troca.aprovado_gestor_por = request.user
        troca.motivo_rejeicao = data.get('motivo_rejeicao', 'Rejeitado pelo gestor.')
        troca.save()
        return JsonResponse({'success': True, 'troca': _serializar_troca(troca)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['DELETE'])
def api_troca_delete(request, pk):
    """Cancela (ou exclui) uma solicitação pendente."""
    try:
        troca = get_object_or_404(TrocaFolga, pk=pk)
        if troca.status not in ['pendente_analista', 'pendente_gestor']:
            return JsonResponse({'error': 'Somente solicitações pendentes podem ser canceladas.'}, status=400)
        troca.status = 'cancelada'
        troca.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_analista_schedule(request, pk):
    """Retorna as folgas manuais de um analista (para preview no Cenário 2)."""
    analista = get_object_or_404(AnalistaEscala, pk=pk)
    rascunho_id = request.GET.get('rascunho_id')
    if rascunho_id:
        folgas = FolgaManual.objects.filter(analista=analista, rascunho_id=rascunho_id)
    else:
        folgas = FolgaManual.objects.filter(analista=analista, rascunho__isnull=True)

    data = {}
    for f in folgas:
        key = f"{f.data.year}-{str(f.data.month).zfill(2)}-{str(f.data.day).zfill(2)}"
        data[key] = {'tipo': f.tipo, 'motivo': f.motivo}

    return JsonResponse({
        'analista_id': analista.id,
        'analista_nome': analista.nome,
        'modelo_escala_id': str(analista.modelo_escala_id) if analista.modelo_escala_id else None,
        'data_primeira_folga': analista.data_primeira_folga.isoformat() if analista.data_primeira_folga else None,
        'turno': analista.turno.nome if analista.turno else None,
        'turno_horario': analista.turno.horario if analista.turno else None,
        'folgas_manuais': data,
    })
