from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models import AuditoriaAtendimento, ConfiguracaoAuditoria, User, Department


# ========================================
# DECORADORES DE PERMISSÃO
# ========================================

def gestor_or_admin_required(view_func):
    """Decorator para permitir apenas gestores e administradores"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        if not (request.user.is_gestor() or request.user.is_administrador()):
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def gestor_admin_or_analyst_required(view_func):
    """Decorator para permitir gestores, administradores e analistas"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        if not (request.user.is_gestor() or request.user.is_administrador() or request.user.is_analista()):
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator para permitir apenas administradores"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_administrador():
            return JsonResponse({'error': 'Acesso negado. Apenas administradores.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# ========================================
# CRUD DE AUDITORIAS
# ========================================

@gestor_or_admin_required
@require_POST
def api_auditoria_create(request):
    """Cria nova auditoria de atendimento"""
    try:
        data = json.loads(request.body)
        
        # Obter departamento com fallback para ID 1 (NRS Suporte)
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
        
        if not department:
            # Fallback: Tentar pegar NRS Suporte (ID 1) ou o primeiro disponível
            department = Department.objects.filter(id=1).first() or Department.objects.first()
            
        if not department:
            return JsonResponse({'error': 'Nenhum departamento encontrado no sistema'}, status=400)
        
        # Validar campos obrigatórios
        required_fields = ['data_atendimento', 'id_conversa', 'tipo_atendimento', 'analista_auditado_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'Campo obrigatório: {field}'}, status=400)
        
        # Validar analista
        try:
            analista = User.objects.get(id=data['analista_auditado_id'])
        except User.DoesNotExist:
            return JsonResponse({'error': 'Analista não encontrado'}, status=404)
        
        # Validar descrições de erro quando critério = False
        criterios_erros = {
            'apresentou_corretamente': 'erro_apresentacao',
            'analisou_historico': 'erro_historico',
            'entendeu_solicitacao': 'erro_entendimento',
            'informacao_clara': 'erro_informacao',
            'acordo_espera': 'erro_acordo_espera',
            'atendimento_respeitoso': 'erro_respeito',
            'portugues_correto': 'erro_portugues',
            'finalizacao_correta': 'erro_finalizacao',
            'procedimento_correto': 'erro_procedimento',
        }
        
        for criterio, campo_erro in criterios_erros.items():
            if not data.get(criterio, True) and not data.get(campo_erro, '').strip():
                return JsonResponse({
                    'error': f'Descrição do erro é obrigatória quando o critério "{criterio}" não é atendido'
                }, status=400)
        
        # Bloquear duplicidade no mesmo departamento
        id_conversa = data.get('id_conversa', '').strip()
        if AuditoriaAtendimento.objects.filter(id_conversa=id_conversa, department=department).exists():
            return JsonResponse({
                'error': f'Já existe uma auditoria registrada para a conversa "{id_conversa}" neste departamento.'
            }, status=400)
        
        # Criar auditoria
        auditoria = AuditoriaAtendimento(
            data_atendimento=data['data_atendimento'],
            id_conversa=data['id_conversa'],
            link_conversa=data.get('link_conversa'),
            tipo_atendimento=data['tipo_atendimento'],
            analista_auditado=analista,
            auditor=request.user,
            department=department,
            # Critérios
            apresentou_corretamente=data.get('apresentou_corretamente', True),
            erro_apresentacao=data.get('erro_apresentacao', ''),
            analisou_historico=data.get('analisou_historico', True),
            erro_historico=data.get('erro_historico', ''),
            entendeu_solicitacao=data.get('entendeu_solicitacao', True),
            erro_entendimento=data.get('erro_entendimento', ''),
            informacao_clara=data.get('informacao_clara', True),
            erro_informacao=data.get('erro_informacao', ''),
            acordo_espera=data.get('acordo_espera', True),
            erro_acordo_espera=data.get('erro_acordo_espera', ''),
            atendimento_respeitoso=data.get('atendimento_respeitoso', True),
            erro_respeito=data.get('erro_respeito', ''),
            portugues_correto=data.get('portugues_correto', True),
            erro_portugues=data.get('erro_portugues', ''),
            finalizacao_correta=data.get('finalizacao_correta', True),
            erro_finalizacao=data.get('erro_finalizacao', ''),
            procedimento_correto=data.get('procedimento_correto', True),
            erro_procedimento=data.get('erro_procedimento', ''),
            # Evidências visuais por critério (opcional)
            imagem_erro_apresentacao=data.get('imagem_erro_apresentacao', '') or None,
            imagem_erro_historico=data.get('imagem_erro_historico', '') or None,
            imagem_erro_entendimento=data.get('imagem_erro_entendimento', '') or None,
            imagem_erro_informacao=data.get('imagem_erro_informacao', '') or None,
            imagem_erro_acordo_espera=data.get('imagem_erro_acordo_espera', '') or None,
            imagem_erro_respeito=data.get('imagem_erro_respeito', '') or None,
            imagem_erro_portugues=data.get('imagem_erro_portugues', '') or None,
            imagem_erro_finalizacao=data.get('imagem_erro_finalizacao', '') or None,
            imagem_erro_procedimento=data.get('imagem_erro_procedimento', '') or None,
        )
        
        # Save já calcula automaticamente pontuação, nota e classificação
        auditoria.save()
        
        return JsonResponse({
            'success': True,
            'auditoria': {
                'id': str(auditoria.id),
                'pontuacao': auditoria.pontuacao,
                'nota': float(auditoria.nota),
                'classificacao': auditoria.classificacao,
                'requer_acao': auditoria.requer_acao,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gestor_admin_or_analyst_required
@require_GET
def api_auditoria_list(request):
    """Lista auditorias com filtros opcionais"""
    try:
        # Obter departamento
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
            
        if not department:
            department = Department.objects.filter(id=1).first() or Department.objects.first()
            
        if not department:
            return JsonResponse({'error': 'Nenhum departamento encontrado'}, status=400)
        
        # Testar se as colunas novas existem no banco
        has_new_columns = True
        try:
            # Uma query simples que tenta acessar uma das colunas novas
            AuditoriaAtendimento.objects.only('id', 'ciente_analista').first()
        except Exception:
            has_new_columns = False
        
        # Base queryset
        queryset = AuditoriaAtendimento.objects.filter(department=department).select_related('analista_auditado', 'auditor')

        if not has_new_columns:
            queryset = queryset.defer('ciente_analista', 'data_ciente')

        # Se for analista, filtrar apenas as suas próprias auditorias
        if request.user.is_analista():
            queryset = queryset.filter(analista_auditado=request.user)

        
        # Filtros
        analista_id = request.GET.get('analista_id')
        if analista_id:
            queryset = queryset.filter(analista_auditado_id=analista_id)
        
        data_inicio = request.GET.get('data_inicio')
        if data_inicio:
            queryset = queryset.filter(data_atendimento__gte=data_inicio)
        
        data_fim = request.GET.get('data_fim')
        if data_fim:
            queryset = queryset.filter(data_atendimento__lte=data_fim)
        
        tipo = request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_atendimento=tipo)
        
        classificacao = request.GET.get('classificacao')
        if classificacao:
            queryset = queryset.filter(classificacao=classificacao)
        
        apenas_alertas = request.GET.get('apenas_alertas')
        if apenas_alertas == 'true':
            queryset = queryset.filter(requer_acao=True)
        
        # Ordenar por data de criação da auditoria (mais recentes primeiro)
        queryset = queryset.order_by('-created_at')
        
        # Paginação
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        start = (page - 1) * per_page
        end = start + per_page
        
        total = queryset.count()
        auditorias = queryset[start:end]
        
        data = []
        for aud in auditorias:
            data.append({
                'id': str(aud.id),
                'data_atendimento': aud.data_atendimento.isoformat(),
                'id_conversa': aud.id_conversa,
                'link_conversa': aud.link_conversa,
                'tipo_atendimento': aud.get_tipo_atendimento_display(),
                'analista_auditado': {
                    'id': str(aud.analista_auditado.id),
                    'username': aud.analista_auditado.username,
                    'nome_completo': aud.analista_auditado.get_full_name() or aud.analista_auditado.username,
                },
                'auditor': {
                    'id': str(aud.auditor.id),
                    'username': aud.auditor.username,
                } if not request.user.is_analista() else None,
                'pontuacao': aud.pontuacao,
                'nota': float(aud.nota),
                'classificacao': aud.classificacao,
                'classificacao_display': aud.get_classificacao_display(),
                'requer_acao': aud.requer_acao,
                'feedback_data': aud.feedback_data.isoformat() if aud.feedback_data else None,
                'feedback_gestor': aud.feedback_gestor.get_full_name() if aud.feedback_gestor else None,
                'created_at': aud.created_at.isoformat(),
                'ciente_analista': aud.ciente_analista if has_new_columns else False,
                'data_ciente': aud.data_ciente.isoformat() if has_new_columns and aud.data_ciente else None,
                'can_edit': request.user.is_gestor() or request.user.is_administrador(),
                'can_delete': request.user.is_gestor() or request.user.is_administrador(),
            })
        
        return JsonResponse({
            'success': True,
            'auditorias': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gestor_admin_or_analyst_required
@require_GET
def api_auditoria_detail(request, pk):
    """Detalhes de uma auditoria específica"""
    print(f"[AUDIT DEBUG] detail context: user={request.user.username}, pk={pk}, method={request.method}")
    try:
        # Verificar se as colunas novas existem
        has_new_columns = True
        try:
            # Tentar um fetch simples com as colunas novas
            AuditoriaAtendimento.objects.only('id', 'ciente_analista').get(id=pk)
        except Exception:
            has_new_columns = False

        # Buscar a auditoria (com ou sem as colunas novas)
        queryset = AuditoriaAtendimento.objects.select_related('analista_auditado', 'auditor', 'feedback_gestor')
        if not has_new_columns:
            queryset = queryset.defer('ciente_analista', 'data_ciente')
            
        auditoria = queryset.get(id=pk)
            
        if not request.user.is_gestor() and not request.user.is_administrador():
            # Se for analista, só pode ver sua própria auditoria
            if auditoria.analista_auditado != request.user:
                return JsonResponse({'error': 'Acesso negado'}, status=403)
            
            # Verificar departamento para analista
            department = request.session.get('current_department_obj') or request.user.department
            if isinstance(department, dict):
                department = Department.objects.filter(id=department['id']).first()
            
            if auditoria.department != department:
                return JsonResponse({'error': 'Acesso negado (departamento)'}, status=403)

        data = {
            'id': str(auditoria.id),
            'data_atendimento': auditoria.data_atendimento.isoformat(),
            'id_conversa': auditoria.id_conversa,
            'link_conversa': auditoria.link_conversa,
            'tipo_atendimento': auditoria.get_tipo_atendimento_display(),
            'tipo_atendimento_key': auditoria.tipo_atendimento,
            'analista_auditado': {
                'id': str(auditoria.analista_auditado.id),
                'username': auditoria.analista_auditado.username,
                'nome_completo': auditoria.analista_auditado.get_full_name() or auditoria.analista_auditado.username,
            },
            'auditor': {
                'id': str(auditoria.auditor.id),
                'username': auditoria.auditor.username,
                'nome_completo': auditoria.auditor.get_full_name() or auditoria.auditor.username,
            } if not request.user.is_analista() else None,
            'can_edit': request.user.is_gestor() or request.user.is_administrador(),
            'can_delete': request.user.is_gestor() or request.user.is_administrador(),
            'criterios': {
                'apresentou_corretamente': auditoria.apresentou_corretamente,
                'erro_apresentacao': auditoria.erro_apresentacao,
                'imagem_erro_apresentacao': auditoria.imagem_erro_apresentacao or '',
                'analisou_historico': auditoria.analisou_historico,
                'erro_historico': auditoria.erro_historico,
                'imagem_erro_historico': auditoria.imagem_erro_historico or '',
                'entendeu_solicitacao': auditoria.entendeu_solicitacao,
                'erro_entendimento': auditoria.erro_entendimento,
                'imagem_erro_entendimento': auditoria.imagem_erro_entendimento or '',
                'informacao_clara': auditoria.informacao_clara,
                'erro_informacao': auditoria.erro_informacao,
                'imagem_erro_informacao': auditoria.imagem_erro_informacao or '',
                'acordo_espera': auditoria.acordo_espera,
                'erro_acordo_espera': auditoria.erro_acordo_espera,
                'imagem_erro_acordo_espera': auditoria.imagem_erro_acordo_espera or '',
                'atendimento_respeitoso': auditoria.atendimento_respeitoso,
                'erro_respeito': auditoria.erro_respeito,
                'imagem_erro_respeito': auditoria.imagem_erro_respeito or '',
                'portugues_correto': auditoria.portugues_correto,
                'erro_portugues': auditoria.erro_portugues,
                'imagem_erro_portugues': auditoria.imagem_erro_portugues or '',
                'finalizacao_correta': auditoria.finalizacao_correta,
                'erro_finalizacao': auditoria.erro_finalizacao,
                'imagem_erro_finalizacao': auditoria.imagem_erro_finalizacao or '',
                'procedimento_correto': auditoria.procedimento_correto,
                'erro_procedimento': auditoria.erro_procedimento,
                'imagem_erro_procedimento': auditoria.imagem_erro_procedimento or '',
            },
            'pontuacao': auditoria.pontuacao,
            'nota': float(auditoria.nota),
            'classificacao': auditoria.classificacao,
            'classificacao_display': auditoria.get_classificacao_display(),
            'requer_acao': auditoria.requer_acao,
            'feedback_data': auditoria.feedback_data.isoformat() if auditoria.feedback_data else None,
            'feedback_gestor': auditoria.feedback_gestor.get_full_name() if auditoria.feedback_gestor else None,
            'created_at': auditoria.created_at.isoformat(),
            'updated_at': auditoria.updated_at.isoformat(),
            'ciente_analista': auditoria.ciente_analista if has_new_columns else False,
            'data_ciente': auditoria.data_ciente.isoformat() if has_new_columns and auditoria.data_ciente else None,
        }
        
        return JsonResponse({'success': True, 'auditoria': data})
        
    except AuditoriaAtendimento.DoesNotExist:
        print(f"[AUDIT DEBUG] detail: auditoria {pk} not found")
        return JsonResponse({'error': 'Auditoria não encontrada'}, status=404)
    except Exception as e:
        print(f"[AUDIT DEBUG] detail: error {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@gestor_or_admin_required
@require_POST
def api_auditoria_update(request, pk):
    """Atualiza uma auditoria (gestor e admin)"""
    print(f"[AUDIT DEBUG] update start: pk={pk}, user={request.user.username}")
    try:
        auditoria = AuditoriaAtendimento.objects.get(id=pk)
        data = json.loads(request.body)
        
        # Atualizar campos editáveis
        if 'data_atendimento' in data:
            auditoria.data_atendimento = data['data_atendimento']
        if 'id_conversa' in data:
            new_id = data['id_conversa'].strip()
            # Verificar se já existe EM OUTRA auditoria no mesmo departamento
            if AuditoriaAtendimento.objects.filter(
                id_conversa=new_id, 
                department=auditoria.department
            ).exclude(id=pk).exists():
                return JsonResponse({
                    'error': f'Já existe outra auditoria com o ID de conversa "{new_id}" neste departamento.'
                }, status=400)
            auditoria.id_conversa = new_id
        if 'tipo_atendimento' in data:
            auditoria.tipo_atendimento = data['tipo_atendimento']
        if 'link_conversa' in data:
            auditoria.link_conversa = data['link_conversa']
        
        # Atualizar critérios
        criterios = [
            'apresentou_corretamente', 'analisou_historico', 'entendeu_solicitacao',
            'informacao_clara', 'acordo_espera', 'atendimento_respeitoso',
            'portugues_correto', 'finalizacao_correta', 'procedimento_correto'
        ]
        
        erros = [
            'erro_apresentacao', 'erro_historico', 'erro_entendimento',
            'erro_informacao', 'erro_acordo_espera', 'erro_respeito',
            'erro_portugues', 'erro_finalizacao', 'erro_procedimento'
        ]
        
        for criterio in criterios:
            if criterio in data:
                setattr(auditoria, criterio, data[criterio])
        
        for erro in erros:
            if erro in data:
                setattr(auditoria, erro, data[erro])
        
        # Save recalcula automaticamente
        auditoria.save()
        
        return JsonResponse({
            'success': True,
            'auditoria': {
                'id': str(auditoria.id),
                'pontuacao': auditoria.pontuacao,
                'nota': float(auditoria.nota),
                'classificacao': auditoria.classificacao,
                'requer_acao': auditoria.requer_acao,
            }
        })
        
    except AuditoriaAtendimento.DoesNotExist:
        print(f"[AUDIT DEBUG] update: auditoria {pk} not found")
        return JsonResponse({'error': 'Auditoria não encontrada'}, status=404)
    except Exception as e:
        print(f"[AUDIT DEBUG] update: error {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@gestor_or_admin_required
@require_POST
def api_auditoria_delete(request, pk):
    """Exclui uma auditoria (gestor e admin)"""
    try:
        # Garantir que pertence ao departamento ou que o usuário tem permissão total
        auditoria = AuditoriaAtendimento.objects.get(id=pk)
        
        # Log de segurança (opcional)
        print(f"[AUDIT] Excluindo auditoria {pk} - ID Conversa: {auditoria.id_conversa} por {request.user.username}")
        print(f"[AUDIT DEBUG] delete: Excluindo auditoria {pk} - ID Conversa: {auditoria.id_conversa} por {request.user.username}")
        
        auditoria.delete()
        return JsonResponse({'success': True})
    except AuditoriaAtendimento.DoesNotExist:
        # Se não encontrar por ID, pode ser que o PK enviado esteja errado ou já deletado
        print(f"[AUDIT DEBUG] delete: Auditoria {pk} não encontrada")
        return JsonResponse({'error': 'Auditoria não encontrada ou já excluída.'}, status=404)
    except Exception as e:
        print(f"[AUDIT DEBUG] delete: Erro inesperado {pk}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Erro ao excluir: {str(e)}'}, status=500)


# ========================================
# ESTATÍSTICAS E RANKING
# ========================================

@gestor_or_admin_required
@require_GET
def api_ranking_analistas(request):
    """Ranking de analistas por nota média (Otimizado)"""
    try:
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
            
        if not department:
             department = Department.objects.filter(id=1).first() or Department.objects.first()
        
        # Período opcional
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        
        queryset = AuditoriaAtendimento.objects.filter(department=department)
        
        if data_inicio:
            queryset = queryset.filter(data_atendimento__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_atendimento__lte=data_fim)
        
        # Agrupar por analista e calcular médias
        ranking = queryset.values(
            'analista_auditado__id',
            'analista_auditado__username',
            'analista_auditado__first_name',
            'analista_auditado__last_name'
        ).annotate(
            total_auditorias=Count('id'),
            nota_media=Avg('nota'),
            pontuacao_media=Avg('pontuacao')
        ).order_by('-nota_media')

        # OTIMIZAÇÃO: Buscar classificações agrupadas em uma única query
        # Em vez de fazer uma query para cada analista no loop
        classificacoes_raw = queryset.values(
            'analista_auditado__id', 'classificacao'
        ).annotate(count=Count('id'))
        
        # Processar em memória para acesso rápido (dict of dicts ou dict of lists)
        from collections import defaultdict
        classificacoes_map = defaultdict(list)
        for item in classificacoes_raw:
            classificacoes_map[item['analista_auditado__id']].append({
                'classificacao': item['classificacao'],
                'count': item['count']
            })
        
        # Formatar resposta com posição
        data = []
        for idx, item in enumerate(ranking, 1):
            analista_id = item['analista_auditado__id']
            
            # Determinar classificação predominante via Python (já carregado)
            class_list = classificacoes_map.get(analista_id, [])
            # Ordenar por count decrescente para pegar a moda
            class_list.sort(key=lambda x: x['count'], reverse=True)
            
            classificacao_predominante = class_list[0]['classificacao'] if class_list else 'N/A'
            
            nome_completo = f"{item['analista_auditado__first_name']} {item['analista_auditado__last_name']}".strip()
            if not nome_completo:
                nome_completo = item['analista_auditado__username']
            
            data.append({
                'posicao': idx,
                'analista_id': str(analista_id),
                'analista_username': item['analista_auditado__username'],
                'analista_nome': nome_completo,
                'total_auditorias': item['total_auditorias'],
                'nota_media': round(float(item['nota_media']), 2),
                'pontuacao_media': round(float(item['pontuacao_media']), 1),
                'classificacao_predominante': classificacao_predominante,
            })
        
        return JsonResponse({'success': True, 'ranking': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gestor_or_admin_required
@require_GET
def api_estatisticas_analista(request, analista_id):
    """Estatísticas detalhadas de um analista específico"""
    try:
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
            
        if not department:
             department = Department.objects.filter(id=1).first() or Department.objects.first()
        
        analista = User.objects.get(id=analista_id)
        
        auditorias = AuditoriaAtendimento.objects.filter(
            department=department,
            analista_auditado=analista
        )
        
        total_auditorias = auditorias.count()
        
        if total_auditorias == 0:
            return JsonResponse({
                'success': True,
                'analista': {
                    'id': str(analista.id),
                    'username': analista.username,
                    'nome_completo': analista.get_full_name() or analista.username,
                },
                'total_auditorias': 0,
                'nota_media': 0,
                'distribuicao': {},
                'ultima_auditoria': None,
                'tem_alertas': False,
            })
        
        # Calcular estatísticas
        nota_media = auditorias.aggregate(Avg('nota'))['nota__avg']
        
        # Distribuição por classificação — OTIMIZADO: 1 query em vez de 4
        dist_data = auditorias.values('classificacao').annotate(count=Count('id'))
        distribuicao = {'excelente': 0, 'bom': 0, 'regular': 0, 'insatisfatorio': 0}
        for item in dist_data:
            if item['classificacao'] in distribuicao:
                distribuicao[item['classificacao']] = item['count']
        
        # Última auditoria
        ultima = auditorias.order_by('-created_at').first()
        
        # Verificar alertas ativos
        tem_alertas = auditorias.filter(requer_acao=True).exists()
        
        return JsonResponse({
            'success': True,
            'analista': {
                'id': str(analista.id),
                'username': analista.username,
                'nome_completo': analista.get_full_name() or analista.username,
            },
            'total_auditorias': total_auditorias,
            'nota_media': round(float(nota_media), 2),
            'distribuicao': distribuicao,
            'ultima_auditoria': {
                'id': ultima.id,
                'data': timezone.localtime(ultima.created_at).date().isoformat(),
                'nota': float(ultima.nota),
                'classificacao': ultima.get_classificacao_display(),
            } if ultima else None,
            'tem_alertas': tem_alertas,
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'Analista não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gestor_admin_or_analyst_required
@require_GET
def api_dashboard_auditoria(request):
    """Dashboard geral de auditorias"""
    try:
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
            
        if not department:
             department = Department.objects.filter(id=1).first() or Department.objects.first()
        
        # Período opcional (padrão: último mês)
        data_fim = timezone.now().date()
        data_inicio = data_fim - timedelta(days=30)
        
        if request.GET.get('data_inicio'):
            data_inicio = datetime.strptime(request.GET.get('data_inicio'), '%Y-%m-%d').date()
        if request.GET.get('data_fim'):
            data_fim = datetime.strptime(request.GET.get('data_fim'), '%Y-%m-%d').date()
        
        auditorias = AuditoriaAtendimento.objects.filter(
            department=department,
            data_atendimento__gte=data_inicio,
            data_atendimento__lte=data_fim
        )

        # Se for analista, filtrar apenas as suas próprias auditorias
        if request.user.is_analista():
            auditorias = auditorias.filter(analista_auditado=request.user)

        
        total = auditorias.count()
        nota_media_geral = auditorias.aggregate(Avg('nota'))['nota__avg'] or 0
        
        # Distribuição por classificação
        # Distribuição por classificação - Otimizado (1 query em vez de 4)
        dist_data = auditorias.values('classificacao').annotate(total=Count('id'))
        distribuicao = {
            'excelente': 0,
            'bom': 0,
            'regular': 0,
            'insatisfatorio': 0
        }
        for item in dist_data:
            if item['classificacao'] in distribuicao:
                distribuicao[item['classificacao']] = item['total']
        
        # Analistas com alertas
        analistas_com_alertas = auditorias.filter(requer_acao=True).values(
            'analista_auditado__id',
            'analista_auditado__username'
        ).distinct()
        
        # Top 3 analistas
        top_3 = auditorias.values(
            'analista_auditado__id',
            'analista_auditado__username',
            'analista_auditado__first_name',
            'analista_auditado__last_name'
        ).annotate(
            nota_media=Avg('nota')
        ).order_by('-nota_media')[:3]
        
        return JsonResponse({
            'success': True,
            'periodo': {
                'inicio': data_inicio.isoformat(),
                'fim': data_fim.isoformat(),
            },
            'total_auditorias': total,
            'nota_media_geral': round(float(nota_media_geral), 2),
            'distribuicao': distribuicao,
            'total_alertas': auditorias.filter(requer_acao=True).count(),
            'analistas_com_alertas': [{'id': str(a['analista_auditado__id']), 'username': a['analista_auditado__username']} for a in analistas_com_alertas],
            'top_3': [
                {
                    'id': str(item['analista_auditado__id']),
                    'username': item['analista_auditado__username'],
                    'nome': f"{item['analista_auditado__first_name']} {item['analista_auditado__last_name']}".strip() or item['analista_auditado__username'],
                    'nota_media': round(float(item['nota_media']), 2),
                }
                for item in top_3
            ],
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========================================
# CONFIGURAÇÕES
# ========================================

@gestor_or_admin_required
@require_GET
def api_configuracao_get(request):
    """Obter configuração atual de auditoria"""
    try:
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
        
        if not department:
            department = Department.objects.filter(id=1).first() or Department.objects.first()
            
        if not department:
            return JsonResponse({'error': 'Nenhum departamento encontrado'}, status=400)
        
        config, created = ConfiguracaoAuditoria.objects.get_or_create(
            department=department,
            defaults={'percentual_minimo_aceitavel': 77.78, 'ativo': True}
        )
        
        return JsonResponse({
            'success': True,
            'configuracao': {
                'id': str(config.id),
                'percentual_minimo_aceitavel': float(config.percentual_minimo_aceitavel),
                'ativo': config.ativo,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@admin_required
@require_POST
def api_configuracao_update(request):
    """Atualizar configuração (apenas admin)"""
    try:
        data = json.loads(request.body)
        
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
        
        config, created = ConfiguracaoAuditoria.objects.get_or_create(department=department)
        
        if 'percentual_minimo_aceitavel' in data:
            percentual = float(data['percentual_minimo_aceitavel'])
            if percentual < 0 or percentual > 100:
                return JsonResponse({'error': 'Percentual deve estar entre 0 e 100'}, status=400)
            config.percentual_minimo_aceitavel = percentual
        
        if 'ativo' in data:
            config.ativo = bool(data['ativo'])
        
        config.save()
        
        return JsonResponse({
            'success': True,
            'configuracao': {
                'id': str(config.id),
                'percentual_minimo_aceitavel': float(config.percentual_minimo_aceitavel),
                'ativo': config.ativo,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========================================
# HELPER - LISTA DE ANALISTAS
# ========================================

@gestor_or_admin_required
@require_GET
def api_analistas_list(request):
    """Lista de analistas do departamento para seleção"""
    try:
        department = request.session.get('current_department_obj') or request.user.department
        if isinstance(department, dict):
            department = Department.objects.get(id=department['id'])
            
        if not department:
             department = Department.objects.filter(id=1).first() or Department.objects.first()
             
        if not department:
             return JsonResponse({'error': 'Nenhum departamento encontrado'}, status=400)
        
        # Filtrar apenas usuários com role='analista' (excluindo gestores e administradores)
        analistas = User.objects.filter(
            department=department,
            role='analista',  # Apenas analistas
            ativo=True
        ).order_by('first_name', 'last_name', 'username')
        
        data = []
        for analista in analistas:
            nome_completo = analista.get_full_name() or analista.username
            data.append({
                'id': str(analista.id),
                'username': analista.username,
                'nome_completo': nome_completo,
                'role': analista.get_role_display(),
            })
        
        return JsonResponse({'success': True, 'analistas': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========================================
# FEEDBACK / CONVERSA COM ANALISTA
# ========================================

@gestor_or_admin_required
@require_POST
def api_registrar_feedback(request, pk):
    """Registra a data de conversa com o analista sobre um alerta de auditoria"""
    try:
        auditoria = AuditoriaAtendimento.objects.get(id=pk)
        data = json.loads(request.body)
        
        if 'feedback_data' in data:
            auditoria.feedback_data = data['feedback_data']
            auditoria.feedback_gestor = request.user
            auditoria.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Data de feedback não informada'}, status=400)
            
    except AuditoriaAtendimento.DoesNotExist:
        return JsonResponse({'error': 'Auditoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gestor_or_admin_required
@require_GET
def api_check_conversation_id(request):
    """Verifica se um ID de conversa já foi auditado no departamento do usuário"""
    id_conversa = request.GET.get('id')
    if not id_conversa:
        return JsonResponse({'error': 'ID não informado'}, status=400)
    
    department = request.session.get('current_department_obj') or request.user.department
    if isinstance(department, dict):
        department = Department.objects.get(id=department['id'])
        
    exists = AuditoriaAtendimento.objects.filter(
        id_conversa=id_conversa,
        department=department
    ).exists()
    
    return JsonResponse({'exists': exists})


@gestor_admin_or_analyst_required
@require_POST
def api_registrar_ciente(request, pk):
    """Registra o ciente do analista sobre a auditoria realizada"""
    try:
        auditoria = AuditoriaAtendimento.objects.get(id=pk)
        
        # Apenas o analista auditado daquela auditoria pode dar o ciente
        if auditoria.analista_auditado != request.user:
             return JsonResponse({'error': 'Ação permitida apenas para o analista auditado'}, status=403)
        
        if auditoria.ciente_analista:
            return JsonResponse({'error': 'Ciente já registrado anteriormente'}, status=400)
            
        auditoria.ciente_analista = True
        auditoria.data_ciente = timezone.now()
        auditoria.save()
        
        return JsonResponse({
            'success': True,
            'data_ciente': auditoria.data_ciente.isoformat()
        })
        
    except AuditoriaAtendimento.DoesNotExist:
        return JsonResponse({'error': 'Auditoria não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
