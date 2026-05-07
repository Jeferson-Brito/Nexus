from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from datetime import datetime

from ..models import Turno, AnalistaEscala, FolgaManual, EscalaRascunho, ModeloEscala, ConfiguracaoEscala
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
            
        return JsonResponse({'success': True, 'id': str(modelo.id)})
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
        rascunho_id = data.get('rascunho_id')
        rascunho = EscalaRascunho.objects.get(id=rascunho_id) if rascunho_id else None
        
        turno = Turno.objects.create(
            nome=data.get('nome', ''),
            horario=data.get('horario', ''),
            cor=data.get('cor', '#2563eb'),
            ordem=data.get('ordem', 0),
            rascunho=rascunho
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

        # Mapeamento para associar analistas aos novos turnos
        mapa_turnos = {}
        
        turnos_criados = []
        for t in turnos_fonte:
            novo_t = Turno.objects.create(
                rascunho=rascunho_destino,
                nome=t.nome,
                horario=t.horario,
                cor=t.cor,
                ordem=t.ordem,
                ativo=t.ativo
            )
            mapa_turnos[t.id] = novo_t
            
            turnos_criados.append({
                'id': novo_t.id,
                'nome': novo_t.nome,
                'horario': novo_t.horario,
                'cor': novo_t.cor
            })

        # Copiar Analistas
        for a in analistas_fonte:
            novo_turno = mapa_turnos.get(a.turno_id) if a.turno else None
            
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
