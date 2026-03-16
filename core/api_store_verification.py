"""
APIs para o Sistema de Verificação de Lojas - Notificações e Timers
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from datetime import datetime, date, timedelta
from django.db.models import Q
import json
import logging
import time
import random
import math

from .models import (
    Store, StoreAudit, StoreAuditIssue, StoreAuditItem,
    AnalystAssignment, User
)


logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_notify_franchisee(request, issue_id):
    """
    API para notificar franqueado sobre irregularidade
    Abre o modal de escolha de canal (WhatsApp ou Ticket)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    # Retorna dados da irregularidade para o frontend
    irregular_items = []
    for item in issue.items.all():
        irregular_items.append({
            'name': item.get_item_name_display(),
            'description': item.description
        })
    
    return JsonResponse({
        'success': True,
        'issue': {
            'id': str(issue.id),
            'store_code': issue.store.code if issue.store else 'Desconhecida',
            'created_at': issue.created_at.strftime('%d/%m/%Y %H:%M'),
            'irregular_items': irregular_items
        }
    })


@login_required
@require_http_methods(["POST"])
def api_start_whatsapp_notification(request, issue_id):
    """
    Inicia o fluxo de notificação via WhatsApp com timer
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    try:
        data = json.loads(request.body)
        deadline_hours = int(data.get('deadline_hours', 24))
        
        # Validar prazo (24-48 horas)
        if deadline_hours < 24 or deadline_hours > 48:
            return JsonResponse({
                'success': False,
                'error': 'Prazo deve ser entre 24 e 48 horas'
            }, status=400)
        
        # Atualizar issue
        issue.status = 'notificado_whatsapp'
        issue.notification_channel = 'whatsapp'
        issue.deadline_hours = deadline_hours
        issue.timer_started_at = timezone.now()
        issue.deadline_datetime = timezone.now() + timedelta(hours=deadline_hours)
        issue.notified = True
        
        # Adicionar ao histórico
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'user': request.user.get_full_name() or request.user.username,
            'action': 'whatsapp_notification_started',
            'deadline_hours': deadline_hours,
            'deadline_datetime': issue.deadline_datetime.isoformat()
        }
        
        if not isinstance(issue.resolution_history, list):
            issue.resolution_history = []
        issue.resolution_history.append(history_entry)
        
        issue.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Notificação via WhatsApp iniciada. Prazo: {deadline_hours}h',
            'issue': {
                'id': str(issue.id),
                'status': issue.status,
                'deadline_datetime': issue.deadline_datetime.isoformat(),
                'time_remaining_seconds': issue.get_time_remaining()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_create_ticket_from_issue(request, issue_id):
    """
    Cria um ticket a partir de uma irregularidade
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    try:
        data = json.loads(request.body)
        
        # Atualizar issue para status ticket
        issue.status = 'notificado_ticket'
        issue.notification_channel = 'ticket'
        issue.ticket_priority = data.get('priority', 'media')
        issue.ticket_notes = data.get('notes', '')
        
        # Validar e processar deadline_hours de forma segura
        raw_deadline = data.get('deadline_hours')
        try:
            issue.deadline_hours = int(raw_deadline) if raw_deadline is not None else 72
        except (ValueError, TypeError):
            issue.deadline_hours = 72
            
        issue.deadline_datetime = timezone.now() + timedelta(hours=issue.deadline_hours)
        issue.notified = True
        
        # Gerar ID do ticket (pode ser integrado com sistema externo)
        issue.ticket_id = f"TK-{issue.id}-{timezone.now().strftime('%Y%m%d')}"
        
        # Se há responsável, vincular
        responsible_id = data.get('responsible_id')
        if responsible_id:
            try:
                responsible = User.objects.get(id=responsible_id)
                issue.ticket_responsible = responsible
            except User.DoesNotExist:
                pass
        
        # Adicionar ao histórico
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'user': request.user.get_full_name() or request.user.username,
            'action': 'ticket_created',
            'ticket_id': issue.ticket_id,
            'priority': issue.ticket_priority,
            'deadline_hours': issue.deadline_hours
        }
        
        if not isinstance(issue.resolution_history, list):
            issue.resolution_history = []
        issue.resolution_history.append(history_entry)
        
        issue.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Ticket {issue.ticket_id} criado com sucesso',
            'ticket': {
                'id': issue.ticket_id,
                'priority': issue.ticket_priority,
                'deadline_datetime': issue.deadline_datetime.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_mark_issue_resolved(request, issue_id):
    """
    Marca uma irregularidade como resolvida
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    try:
        data = json.loads(request.body)
        notes = data.get('notes', '')
        
        issue.status = 'resolvida'
        issue.resolved_at = timezone.now()
        issue.resolved_by = request.user
        issue.gestor_notes = notes
        
        # Se tinha timer, marca quando terminou
        if issue.timer_started_at and not issue.timer_ended_at:
            issue.timer_ended_at = timezone.now()
        
        # Adicionar ao histórico
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'user': request.user.get_full_name() or request.user.username,
            'action': 'marked_resolved',
            'notes': notes
        }
        
        if not isinstance(issue.resolution_history, list):
            issue.resolution_history = []
        issue.resolution_history.append(history_entry)
        
        issue.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Irregularidade marcada como resolvida'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_timer_status(request, issue_id):
    """
    Retorna o status atual do timer de uma irregularidade
    """
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    time_remaining = issue.get_time_remaining()
    progress_percentage = issue.get_progress_percentage()
    
    # Determina cor do timer
    if progress_percentage < 50:
        timer_color = 'green'
    elif progress_percentage < 75:
        timer_color = 'yellow'
    else:
        timer_color = 'red'
    
    return JsonResponse({
        'success': True,
        'issue_id': str(issue.id),
        'status': issue.status,
        'time_remaining_seconds': time_remaining,
        'progress_percentage': progress_percentage,
        'timer_color': timer_color,
        'deadline_datetime': issue.deadline_datetime.isoformat() if issue.deadline_datetime else None,
        'is_overdue': issue.is_deadline_passed()
    })


@login_required
@require_http_methods(["POST"])
def api_escalate_to_ticket(request, issue_id):
    """
    Escalona automaticamente uma irregularidade WhatsApp para Ticket
    (Quando o prazo vence e não foi resolvido)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    issue = get_object_or_404(StoreAuditIssue, id=issue_id)
    
    try:
        data = json.loads(request.body)
        auto_escalate = data.get('auto_escalate', False)
        
        # Marca que a pergunta de escalonamento foi exibida
        issue.escalation_question_shown = True
        
        if auto_escalate:
            # Muda para ticket automaticamente
            issue.status = 'notificado_ticket'
            issue.auto_escalated = True
            issue.ticket_priority = 'alta'  # Escalonamento automático = prioridade alta
            issue.ticket_id = f"TK-ESC-{issue.id}-{timezone.now().strftime('%Y%m%d')}"
            issue.deadline_hours = 72  # 3 dias para ticket escalonado
            issue.deadline_datetime = timezone.now() + timedelta(hours=72)
            issue.notification_channel = 'ticket'
            
            # Timer do WhatsApp encerrou
            if issue.timer_started_at and not issue.timer_ended_at:
                issue.timer_ended_at = timezone.now()
            
            # Adicionar ao histórico
            history_entry = {
                'timestamp': timezone.now().isoformat(),
                'user': request.user.get_full_name() or request.user.username,
                'action': 'auto_escalated_to_ticket',
                'ticket_id': issue.ticket_id,
                'reason': 'whatsapp_deadline_expired'
            }
            
            if not isinstance(issue.resolution_history, list):
                issue.resolution_history = []
            issue.resolution_history.append(history_entry)
            
            issue.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Irregularidade escalonada para Ticket {issue.ticket_id}',
                'escalated': True,
                'ticket_id': issue.ticket_id
            })
        else:
            # Usuário disse que foi resolvido, não escalona
            issue.status = 'resolvida'
            issue.resolved_at = timezone.now()
            issue.resolved_by = request.user
            
            if issue.timer_started_at and not issue.timer_ended_at:
                issue.timer_ended_at = timezone.now()
            
            history_entry = {
                'timestamp': timezone.now().isoformat(),
                'user': request.user.get_full_name() or request.user.username,
                'action': 'resolved_after_deadline',
                'resolved_via': 'whatsapp'
            }
            
            if not isinstance(issue.resolution_history, list):
                issue.resolution_history = []
            issue.resolution_history.append(history_entry)
            
            issue.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Irregularidade marcada como resolvida',
                'escalated': False
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================================================
# APIs para Gesto de Analistas
# ==================================================

@login_required
@require_http_methods(["GET"])
def api_get_analyst_assignments(request):
    """
    Retorna as lojas atribuídas a um analista específico
    """
    analyst_id = request.GET.get('analyst_id')
    
    if not analyst_id:
        # Se não especificado, retorna do próprio usuário
        analyst_id = request.user.id
    
    # Apenas gestores podem ver atribuições de outros analistas
    if int(analyst_id) != request.user.id and request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    assignments = AnalystAssignment.objects.filter(
        analyst_id=analyst_id,
        active=True
    ).select_related('store')
    
    # OTIMIZAÇÃO: Buscar todas as auditorias da semana para estas lojas de uma vez
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.db.models import Count
    
    today = timezone.localtime(timezone.now()).date()
    start_of_week = today - timedelta(days=today.weekday())
    start_datetime = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    
    # Store IDs atribuídos
    store_ids = [a.store_id for a in assignments]
    
    # Query única para contar auditorias por loja nesta semana
    audit_counts = StoreAudit.objects.filter(
        analyst_id=analyst_id,
        store_id__in=store_ids,
        created_at__gte=start_datetime
    ).values('store_id').annotate(count=Count('id'))
    
    # Map store_id -> count
    counts_map = {item['store_id']: item['count'] for item in audit_counts}
    
    result = []
    for assignment in assignments:
        completed = counts_map.get(assignment.store_id, 0)
        target = assignment.weekly_target
        percentage = (completed / target * 100) if target > 0 else 0
        
        result.append({
            'store_id': str(assignment.store_id),
            'store_code': assignment.store.code,
            'store_city': assignment.store.city,
            'weekly_target': target,
            'progress': {
                'completed': completed,
                'target': target,
                'percentage': round(percentage, 1)
            }
        })
    
    return JsonResponse({'success': True, 'assignments': result})


@login_required
@require_http_methods(["GET"])
def api_get_all_assignments(request):
    """
    Retorna TODAS as atribuições ativas (apenas gestor/admin)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    assignments = AnalystAssignment.objects.filter(active=True).select_related('analyst', 'store').order_by('analyst__first_name', 'store__code')
    
    result = []
    for assignment in assignments:
        progress = assignment.get_weekly_progress()
        result.append({
            'id': str(assignment.id),
            'analyst_name': assignment.analyst.get_full_name() or assignment.analyst.username,
            'store_code': assignment.store.code,
            'store_city': assignment.store.city,
            'weekly_target': assignment.weekly_target,
            'progress': progress,
            'analyst_photo_url': assignment.analyst.profile_photo.url if assignment.analyst.profile_photo else None
        })
    
    return JsonResponse({'success': True, 'assignments': result})


@login_required
@require_http_methods(["POST"])
def api_assign_store_to_analyst(request):
    """
    Atribui uma loja a um analista (apenas gestor/admin)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        data = json.loads(request.body)
        analyst_id = data.get('analyst_id')
        store_id = data.get('store_id')
        weekly_target = data.get('weekly_target', 1)
        
        # Novos parâmetros de período
        period_start_str = data.get('period_start')  # Formato: 'YYYY-MM-DD'
        period_end_str = data.get('period_end')      # Formato: 'YYYY-MM-DD'
        
        analyst = get_object_or_404(User, id=analyst_id)
        store = get_object_or_404(Store, id=store_id)
        
        # Converter strings para date objects
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date() if period_start_str else None
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date() if period_end_str else None
        
        # Validação
        if period_start and period_end and period_start > period_end:
            return JsonResponse({
                'success': False, 
                'error': 'Data de início deve ser anterior à data de fim'
            }, status=400)
        
        assignment, created = AnalystAssignment.objects.get_or_create(
            analyst=analyst,
            store=store,
            defaults={
                'weekly_target': weekly_target,
                'active': True,
                'period_start': period_start,
                'period_end': period_end
            }
        )
        
        if not created:
            assignment.weekly_target = weekly_target
            assignment.active = True
            assignment.period_start = period_start
            assignment.period_end = period_end
            assignment.save()
        
        # Formatar mensagem com datas
        date_info = ""
        if period_start and period_end:
            date_info = f" (Período: {period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')})"
        
        return JsonResponse({
            'success': True,
            'message': f'Loja {store.code} atribuída a {analyst.get_full_name() or analyst.username}{date_info}',
            'created': created
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': 'Formato de data inválido. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_available_stores(request):
    """
    Retorna lojas disponíveis (não atribuídas a nenhum analista)
    E opcionalmente seleciona N lojas aleatórias
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        quantity = request.GET.get('quantity', None)
        
        # Buscar IDs de lojas já atribuídas (ativas)
        assigned_store_ids = AnalystAssignment.objects.filter(
            active=True
        ).values_list('store_id', flat=True).distinct()
        
        # Buscar lojas disponíveis (não atribuídas)
        available_stores = Store.objects.filter(
            active=True
        ).exclude(
            id__in=assigned_store_ids
        ).order_by('code')
        
        total_available = available_stores.count()
        
        # Se quantidade foi especificada, selecionar aleatoriamente
        selected_stores = []
        if quantity:
            try:
                qty = int(quantity)
                if qty > total_available:
                    return JsonResponse({
                        'success': False,
                        'error': f'Apenas {total_available} lojas disponíveis. Solicitado: {qty}'
                    }, status=400)
                
                # Seleção aleatória
                raw_stores = random.sample(list(available_stores.values('id', 'code', 'city')), qty)
                selected_stores = [{'id': str(s['id']), 'code': s['code'], 'city': s['city']} for s in raw_stores]
                
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Quantidade inválida'
                }, status=400)
        else:
            # Retornar todas as disponíveis
            selected_stores = [{'id': str(s['id']), 'code': s['code'], 'city': s['city']} for s in available_stores.values('id', 'code', 'city')]
        
        return JsonResponse({
            'success': True,
            'total_available': total_available,
            'selected_count': len(selected_stores),
            'stores': selected_stores
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_bulk_assign_stores(request):
    """
    Atribui múltiplas lojas a um analista de uma vez
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        data = json.loads(request.body)
        analyst_id = data.get('analyst_id')
        store_ids = data.get('store_ids', [])  # Lista de IDs
        weekly_target = data.get('weekly_target', 1)
        
        # Novos parâmetros de período
        period_start_str = data.get('period_start')
        period_end_str = data.get('period_end')
        
        if not analyst_id or not store_ids:
            return JsonResponse({
                'success': False,
                'error': 'Analista e lojas são obrigatórios'
            }, status=400)
        
        # Converter datas
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date() if period_start_str else None
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date() if period_end_str else None
        
        # Validação
        if period_start and period_end and period_start > period_end:
            return JsonResponse({
                'success': False, 
                'error': 'Data de início deve ser anterior à data de fim'
            }, status=400)
        
        analyst = get_object_or_404(User, id=analyst_id)
        
        # Verificar se alguma loja já está atribuída a outro analista
        already_assigned = AnalystAssignment.objects.filter(
            store_id__in=store_ids,
            active=True
        ).exclude(analyst=analyst).select_related('analyst', 'store')
        
        if already_assigned.exists():
            conflicts = []
            for assignment in already_assigned:
                conflicts.append({
                    'store': assignment.store.code,
                    'analyst': assignment.analyst.get_full_name() or assignment.analyst.username
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Algumas lojas já estão atribuídas a outros analistas',
                'conflicts': conflicts
            }, status=400)
        
        # Criar/atualizar atribuições
        created_count = 0
        updated_count = 0
        
        for store_id in store_ids:
            try:
                store = Store.objects.get(id=store_id, active=True)
                
                assignment, created = AnalystAssignment.objects.get_or_create(
                    analyst=analyst,
                    store=store,
                    defaults={
                        'weekly_target': weekly_target,
                        'active': True,
                        'period_start': period_start,
                        'period_end': period_end
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    assignment.weekly_target = weekly_target
                    assignment.active = True
                    assignment.period_start = period_start
                    assignment.period_end = period_end
                    assignment.save()
                    updated_count += 1
                    
            except Store.DoesNotExist:
                continue
        
        analyst_name = analyst.get_full_name() or analyst.username
        
        # Mensagem com informação de período
        date_info = ""
        if period_start and period_end:
            date_info = f" (Período: {period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')})"
        
        return JsonResponse({
            'success': True,
            'message': f'{created_count + updated_count} lojas atribuídas a {analyst_name}{date_info}',
            'created': created_count,
            'updated': updated_count,
            'total': created_count + updated_count
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': 'Formato de data inválido. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@require_http_methods(["GET"])
def api_get_analyst_dashboard(request):
    """
    Retorna métricas e progresso do analista para dashboard
    """
    analyst_id = request.GET.get('analyst_id', request.user.id)
    
    # Verificar permissão
    if int(analyst_id) != request.user.id and request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    analyst = get_object_or_404(User, id=analyst_id)


def get_daily_quota_info(analyst):
    """
    Helper function to get daily quota information for an analyst.
    Returns dict with quota details.
    """
    from core.models import DailyAuditQuota
    
    daily_quota = DailyAuditQuota.get_or_create_today(analyst)
    
    # Calculate time until midnight (reset time)
    now = timezone.now()
    tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    tomorrow_aware = timezone.make_aware(tomorrow)
    time_until_reset = tomorrow_aware - now
    
    hours_until_reset = int(time_until_reset.total_seconds() // 3600)
    minutes_until_reset = int((time_until_reset.total_seconds() % 3600) // 60)
    
    return {
        'target': daily_quota.daily_quota,
        'completed': daily_quota.audits_completed,
        'remaining': daily_quota.remaining_audits,
        'is_blocked': daily_quota.is_quota_reached,
        'percentage': round(daily_quota.completion_percentage, 1),
        'reset_time': '00:00',
        'hours_until_reset': hours_until_reset,
        'minutes_until_reset': minutes_until_reset
    }


@login_required
@require_http_methods(["GET"])
def api_get_analyst_dashboard(request):
    """Retorna métricas para o dashboard do analista - OTIMIZADO"""
    logger.info(f"[DASHBOARD_START] generating dashboard for user {request.user.username}")
    start_time = time.time()
    
    # 1. Resolver Analista
    analyst_id = request.GET.get('analyst_id')
    if not analyst_id:
        analyst = request.user
    else:
        # Verificar permissão
        if request.user.role == 'analista' and int(request.user.id) != int(analyst_id):
            return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
        analyst = get_object_or_404(User, id=analyst_id)

    # 2. Setup de Datas (Single source of truth)
    now = timezone.now()
    today = now.date()
    # Segunda-feira da semana atual
    start_of_week = today - timedelta(days=today.weekday())
    start_week_aware = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
    
    # Início de Hoje (para queries de auditoria do dia)
    today_start_aware = timezone.make_aware(datetime.combine(today, datetime.min.time()))

    # 3. Bulk Fetch: Assignments (Atribuições)
    # Trazemos Store junto para evitar N+1 no loop
    assignments = AnalystAssignment.objects.filter(
        analyst=analyst, 
        active=True
    ).select_related('store')
    
    total_stores = len(assignments)
    
    # 4. Bulk Fetch: Auditorias da Semana (Query Única)
    # Pegamos todas as auditorias deste analista nesta semana de uma vez
    weekly_audits = StoreAudit.objects.filter(
        analyst=analyst,
        created_at__gte=start_week_aware
    ).values('store_id', 'created_at')
    
    # Processar dados em memória
    stores_audited_this_week = set()
    today_audits_count = 0
    
    for audit in weekly_audits:
        stores_audited_this_week.add(audit['store_id'])
        if audit['created_at'] >= today_start_aware:
            today_audits_count += 1
            
    # 5. Calcular Progresso e Dias Restantes
    days_remaining = None
    days_until_sunday = (6 - today.weekday()) % 7  # Fallback standard
    
    earliest_end_date = None
    
    for assignment in assignments:
        # Calcular dias restantes para esta atribuição específica
        # Lógica replicada de assignment.get_days_remaining() para evitar query extra se houvesse rel
        if assignment.period_end:
            ad_days = 0
            if assignment.period_end >= today:
                ad_days = (assignment.period_end - today).days + 1
            
            if days_remaining is None or ad_days < days_remaining:
                days_remaining = ad_days
                
            if earliest_end_date is None or assignment.period_end < earliest_end_date:
                earliest_end_date = assignment.period_end
        else:
            # Se não tem fim definido, usa a regra padrão de domingo
            if days_remaining is None: # Só define se ainda não definido
                 pass # Vamos deixar o fallback lidar com isso se TUDO for None
    
    # Se nenhum assignments tinha period_end ou days_remaining ainda é None
    if days_remaining is None:
        days_remaining = days_until_sunday if days_until_sunday > 0 else 0
    else:
        # Se misturamos assignments com prazo e sem prazo, o menor prazo (days_remaining calculado) vence
        # Mas precisamos garantir que não ignoramos o "até domingo" se houver assignments sem prazo.
        # Logica simplificada: O menor prazo dita a urgência.
        pass

    # Determinar texto do dia final
    if earliest_end_date:
        day_names = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
        period_end_day = day_names[earliest_end_date.weekday()]
    else:
        period_end_day = 'domingo'

    # 6. Calcular Metas e Percentuais
    stores_verified_count = len(stores_audited_this_week)
    percentage = (stores_verified_count / total_stores * 100) if total_stores > 0 else 0
    percentage = min(100, percentage)
    
    pending_stores = max(0, total_stores - stores_verified_count)
    
    # Meta Diária Dinâmica
    # "Quantas preciso fazer hoje para acabar até o fim do prazo?"
    # divisor = dias restantes (min 1)
    daily_target = 0
    if pending_stores > 0:
        divisor = max(1, days_remaining)
        import math
        daily_target = math.ceil(pending_stores / divisor)

    # 7. Calendário Semanal (Schedule)
    from core.models import DailyAuditQuota
    # Usar get_or_create_today otimizado (cuidado, ele faz save(). Se for gargalo, otimizar depois)
    # Por enquanto, assumimos que 1 write por dashboard load é aceitável, melhor que 50 reads.
    # Mas para visualização pura, talvez não precisasse criar/salvar.
    # Vamos instanciar sem salvar para performance de leitura? 
    # Não, precisamos saber se é working day. Vamos usar o helper mas monitorar o log [DASHBOARD_PERF]
    
    quota_helper = DailyAuditQuota.get_or_create_today(analyst)
    
    weekly_schedule = []
    days_of_week_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    for i in range(7):
        date_check = start_of_week + timedelta(days=i)
        is_today_flag = (date_check == today)
        is_working = quota_helper.is_working_day(date_check)
        
        status = 'work' if is_working else 'off'
        if date_check > today:
            status_display = 'Futuro'
        elif date_check < today:
            status_display = 'Passado'
        else:
            status_display = 'Hoje'
            
        weekly_schedule.append({
            'day_name': days_of_week_names[i],
            'date': date_check.strftime('%d/%m'),
            'is_working': is_working,
            'is_today': is_today_flag,
            'status': status
        })

    # 8. Última Auditoria
    last_audit = StoreAudit.objects.filter(analyst=analyst).order_by('-created_at').first()
    last_audit_date = last_audit.created_at.strftime('%d/%m/%Y %H:%M') if last_audit else None

    # Performance Log
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"[DASHBOARD_PERF] Dashboard gen for {analyst.username} took {duration:.3f}s. Stores: {total_stores}, AuditsWk: {len(weekly_audits)}")

    return JsonResponse({
        'success': True,
        'analyst': {
            'id': str(analyst.id),
            'name': analyst.get_full_name() or analyst.username
        },
        'metrics': {
            'total_stores': total_stores,
            'total_audited': stores_verified_count,
            'total_target': total_stores,
            'progress_percentage': round(percentage, 1),
            'pending': pending_stores,
            'today_audits': today_audits_count,
            'daily_target': daily_target,
            'days_remaining': days_remaining,
            'period_end_day': period_end_day,
            'weekly_schedule': weekly_schedule,
            'last_audit_date': last_audit_date
        },
        'daily_quota': get_daily_quota_info(analyst)
    })


@login_required
@require_http_methods(["GET"])
def api_get_analysts_overview(request):
    """
    Retorna visão geral de todos os analistas para os cards de gestão
    OTIMIZADO: Usa prefetch_related e annotate para reduzir queries
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
        
    try:
        from django.db.models import Count, Prefetch
        from datetime import timedelta, datetime
        
        # Calcular início da semana (segunda-feira)
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_datetime = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Buscar todos os analistas com suas atribuições pré-carregadas
        # Usar Prefetch para carregar assignments com suas lojas e contar auditorias desta semana
        analysts = User.objects.filter(
            role='analista', 
            ativo=True, 
            department__name='NRS Suporte'
        ).prefetch_related(
            Prefetch(
                'store_assignments',
                queryset=AnalystAssignment.objects.filter(active=True).select_related('store')
            )
        ).order_by('first_name')
        
        # 2. Pré-calcular contagem de auditorias de hoje para todos os analistas
        # em uma única query agregada
        today_audits_per_analyst = {}
        today_audit_counts = StoreAudit.objects.filter(
            created_at__gte=today_start
        ).values('analyst_id').annotate(count=Count('id'))
        
        for item in today_audit_counts:
            today_audits_per_analyst[item['analyst_id']] = item['count']
        
        # 3. Pré-calcular contagem de auditorias desta semana por analyst + store
        # em uma única query agregada
        weekly_audits_map = {}
        weekly_audit_counts = StoreAudit.objects.filter(
            created_at__gte=start_datetime
        ).values('analyst_id', 'store_id').annotate(count=Count('id'))
        
        for item in weekly_audit_counts:
            key = (item['analyst_id'], item['store_id'])
            weekly_audits_map[key] = item['count']
        
        # 4. Processar dados dos analistas
        overview_data = []
        current_hour = timezone.now().hour
        
        for analyst in analysts:
            # Usar as atribuições pré-carregadas
            assignments = analyst.store_assignments.all()
            
            total_stores = len(assignments)
            assigned_stores_list = []
            
            # Calcular progresso semanal usando os dados pré-calculados
            weekly_audited = 0
            weekly_target_total = 0
            
            for ass in assignments:
                # Buscar contagem de auditorias do mapa pré-calculado
                key = (analyst.id, ass.store.id)
                audits_this_week = weekly_audits_map.get(key, 0)
                
                # Status da loja para o detalhe
                assigned_stores_list.append({
                    'id': str(ass.store.id),
                    'assignment_id': str(ass.id),
                    'code': ass.store.code,
                    'city': ass.store.city,
                    'last_audit': ass.store.last_audit_date.strftime('%d/%m/%Y %H:%M') if ass.store.last_audit_date else 'Nunca',
                    'status': 'Conforme' if ass.store.last_audit_result == 'conforme' else 'Irregular' if ass.store.last_audit_result == 'irregular' else 'Pendente',
                    'audited_this_week': audits_this_week > 0
                })
                
                weekly_audited += audits_this_week
                weekly_target_total += ass.weekly_target
            
            # Auditorias de hoje (do mapa pré-calculado)
            today_audits = today_audits_per_analyst.get(analyst.id, 0)
            
            # Meta diária dinâmica
            daily_target = max(1, round(total_stores / 5)) if total_stores > 0 else 0
            
            # Status de Atenção
            is_attention = False
            if daily_target > 0:
                progress_pct = (today_audits / daily_target) * 100
                if current_hour >= 16 and progress_pct < 100:
                    is_attention = True
            
            # Ordenar lojas alfabeticamente
            assigned_stores_list.sort(key=lambda x: x['code'])
            
            overview_data.append({
                'id': str(analyst.id),
                'name': analyst.get_full_name() or analyst.username or f"Analista {analyst.id}",
                'photo_url': analyst.profile_photo.url if analyst.profile_photo else None,
                'stats': {
                    'total_stores': total_stores,
                    'weekly_audited': weekly_audited,
                    'weekly_target': weekly_target_total,
                    'weekly_progress_pct': round((weekly_audited / weekly_target_total * 100), 1) if weekly_target_total > 0 else 0,
                    'today_audits': today_audits,
                    'daily_target': daily_target,
                    'pending_weekly': max(0, weekly_target_total - weekly_audited)
                },
                'is_attention': is_attention,
                'stores': assigned_stores_list
            })
            
        return JsonResponse({
            'success': True,
            'analysts': overview_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_unassign_store(request, assignment_id):
    """
    Desvincula uma loja de um analista (apenas gestor/admin)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        assignment = get_object_or_404(AnalystAssignment, id=assignment_id)
        
        # Store info for response
        analyst_name = assignment.analyst.get_full_name() or assignment.analyst.username
        store_code = assignment.store.code
        
        # Deactivate assignment
        assignment.active = False
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Loja {store_code} desvinculada de {analyst_name}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_auto_distribute_stores(request):
    """
    Distribui lojas automaticamente para múltiplos analistas
    Sobras vão para o primeiro analista
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        import json
        import random
        from datetime import datetime
        
        data = json.loads(request.body)
        analyst_ids = data.get('analyst_ids', [])
        weekly_target = int(data.get('weekly_target', 3))
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if not analyst_ids or len(analyst_ids) == 0:
            return JsonResponse({'success': False, 'error': 'Selecione pelo menos um analista'}, status=400)
        
        # Get available stores (active and not assigned)
        assigned_store_ids = AnalystAssignment.objects.filter(active=True).values_list('store_id', flat=True)
        available_stores = list(Store.objects.filter(active=True).exclude(id__in=assigned_store_ids))
        
        if not available_stores:
            return JsonResponse({'success': False, 'error': 'Não há lojas disponíveis para distribuir'}, status=400)
        
        # Randomize stores
        random.shuffle(available_stores)
        
        # Calculate distribution
        total_stores = len(available_stores)
        num_analysts = len(analyst_ids)
        base_per_analyst = total_stores // num_analysts
        remainder = total_stores % num_analysts
        
        # Distribute stores
        distribution = {}
        current_index = 0
        
        for i, analyst_id in enumerate(analyst_ids):
            analyst = get_object_or_404(User, id=analyst_id)
            
            # Distribute remainder: each of the first 'remainder' analysts gets +1
            stores_for_this_analyst = base_per_analyst + (1 if i < remainder else 0)
            
            # Get stores for this analyst
            stores_slice = available_stores[current_index:current_index + stores_for_this_analyst]
            current_index += stores_for_this_analyst
            
            # Create assignments
            for store in stores_slice:
                AnalystAssignment.objects.update_or_create(
                    analyst=analyst,
                    store=store,
                    defaults={
                        'weekly_target': weekly_target,
                        'period_start': period_start if period_start else None,
                        'period_end': period_end if period_end else None,
                        'active': True
                    }
                )
            
            analyst_name = analyst.get_full_name() or analyst.username
            distribution[analyst_name] = stores_for_this_analyst
        
        return JsonResponse({
            'success': True,
            'message': f'{total_stores} lojas distribuídas para {num_analysts} analistas',
            'distribution': distribution,
            'total_stores': total_stores,
            'num_analysts': num_analysts
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in api_auto_distribute_stores: {error_details}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_unassign_all_stores(request):
    """
    Desvincula TODAS as lojas de TODOS os analistas (apenas gestor/admin)
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        # Count active assignments
        active_count = AnalystAssignment.objects.filter(active=True).count()
        
        if active_count == 0:
            return JsonResponse({'success': False, 'error': 'Não há atribuições ativas para remover'}, status=400)
        
        # Deactivate all assignments
        AnalystAssignment.objects.filter(active=True).update(active=False)
        
        return JsonResponse({
            'success': True,
            'message': f'{active_count} atribuições removidas com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_monthly_kpi(request):
    """
    Retorna KPIs das últimas 4-5 semanas do mês atual para o analista
    Mostra desempenho semanal ao longo do mês
    OTIMIZADO: Busca dados em massa para evitar N+1 queries
    """
    from datetime import timedelta, datetime
    from core.models import WeeklyVerificationKPI, AnalystAssignment, StoreAudit
    
    analyst_id = request.GET.get('analyst_id', request.user.id)
    
    # Verificar permissão
    if int(analyst_id) != request.user.id and request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        analyst = get_object_or_404(User, id=analyst_id)
        
        # Buscar semana atual
        today = timezone.now().date()
        start_of_week_today = today - timedelta(days=today.weekday())
        five_weeks_ago = start_of_week_today - timedelta(weeks=4)
        
        # 1. Buscar KPIs existentes (já salvos no banco)
        kpis_db = {
            kpi.week_start_date: kpi 
            for kpi in WeeklyVerificationKPI.objects.filter(
                analyst=analyst,
                week_start_date__gte=five_weeks_ago,
                week_start_date__lte=start_of_week_today
            )
        }
        
        # 2. Buscar atribuições ativas do analista (apenas uma query)
        # Assumimos que as atribuições atuais são as que contam para o histórico recente
        # se não houver registros de KPI congelados para as semanas passadas.
        active_assignments = list(AnalystAssignment.objects.filter(
            analyst=analyst,
            active=True
        ).select_related('store'))
        total_assigned = len(active_assignments)
        
        # 3. Buscar TODAS as auditorias do período (apenas uma query)
        period_start_dt = timezone.make_aware(datetime.combine(five_weeks_ago, datetime.min.time()))
        period_end_dt = timezone.now() # Até o momento atual
        
        all_audits = StoreAudit.objects.filter(
            analyst=analyst,
            created_at__gte=period_start_dt,
            created_at__lte=period_end_dt
        ).values('store_id', 'created_at')
        
        # Organizar auditorias por loja e por semana na memória para acesso rápido
        # Usaremos uma lista de dicts mesmo, ou um mapeamento
        audits_by_store = {}
        for audit in all_audits:
            sid = audit['store_id']
            if sid not in audits_by_store:
                audits_by_store[sid] = []
            audits_by_store[sid].append(audit['created_at'])

        # 4. Preparar dados das 5 semanas
        weeks_data = []
        current_iter_date = five_weeks_ago
        
        for i in range(5):
            week_kpi = kpis_db.get(current_iter_date)
            is_current = (current_iter_date == start_of_week_today)
            
            if week_kpi:
                # KPI já existe e está consolidado no banco
                week_info = {
                    'week_number': i + 1,
                    'week_start': week_kpi.week_start_date.strftime('%d/%m'),
                    'week_end': (week_kpi.week_start_date + timedelta(days=6)).strftime('%d/%m'),
                    'is_current': is_current,
                    'total_assigned': week_kpi.total_assigned_stores,
                    'stores_verified': week_kpi.stores_verified,
                    'total_audits': week_kpi.total_audits_performed,
                    'percentage': float(week_kpi.completion_percentage),
                    'goal_met': week_kpi.goal_met,
                    'status': 'complete' if week_kpi.goal_met else 'incomplete'
                }
            else:
                # Calcular em tempo real para a semana atual ou semanas sem KPI salvo
                week_end = current_iter_date + timedelta(days=6)
                sw_dt = timezone.make_aware(datetime.combine(current_iter_date, datetime.min.time()))
                ew_dt = timezone.make_aware(datetime.combine(week_end, datetime.max.time()))
                
                stores_verified_count = 0
                total_audits_count = 0
                
                for ass in active_assignments:
                    # Verificar auditorias no período para esta loja nos dados em memória
                    store_audits = audits_by_store.get(ass.store_id, [])
                    # Contar quantas auditorias caem nesta semana
                    audits_in_week = [a for a in store_audits if sw_dt <= a <= ew_dt]
                    
                    if audits_in_week:
                        stores_verified_count += 1
                        total_audits_count += len(audits_in_week)
                
                percentage = (stores_verified_count / total_assigned * 100) if total_assigned > 0 else 0
                goal_met = (stores_verified_count >= total_assigned) if total_assigned > 0 else False
                
                week_info = {
                    'week_number': i + 1,
                    'week_start': current_iter_date.strftime('%d/%m'),
                    'week_end': week_end.strftime('%d/%m'),
                    'is_current': is_current,
                    'total_assigned': total_assigned,
                    'stores_verified': stores_verified_count,
                    'total_audits': total_audits_count,
                    'percentage': round(percentage, 1),
                    'goal_met': goal_met,
                    'status': 'current' if is_current else ('complete' if goal_met else 'incomplete')
                }
            
            weeks_data.append(week_info)
            current_iter_date += timedelta(weeks=1)
        
        # 5. Estatísticas Mensais
        # Apenas semanas passadas entram no cálculo de taxa de sucesso
        past_weeks = [w for w in weeks_data if not w['is_current']]
        completed_weeks = sum(1 for w in past_weeks if w['goal_met'])
        total_past_weeks = len(past_weeks)
        monthly_success_rate = (completed_weeks / total_past_weeks * 100) if total_past_weeks > 0 else 0
        
        return JsonResponse({
            'success': True,
            'analyst': {
                'id': str(analyst.id),
                'name': analyst.get_full_name() or analyst.username
            },
            'weeks': weeks_data,
            'monthly_stats': {
                'total_weeks': len(weeks_data),
                'completed_weeks': completed_weeks,
                'success_rate': round(monthly_success_rate, 1)
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error in api_get_monthly_kpi: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_get_all_analysts_monthly_kpi(request):
    """
    Retorna KPIs mensais de todos os analistas para gestores
    ALTAMENTE OTIMIZADO: Busca todos os dados globais em poucas queries
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    from .models import WeeklyVerificationKPI, StoreAudit, AnalystAssignment
    from django.db.models import Prefetch
    
    today = timezone.now().date()
    start_of_week_today = today - timedelta(days=today.weekday())
    five_weeks_ago = start_of_week_today - timedelta(weeks=4)
    period_start_dt = timezone.make_aware(datetime.combine(five_weeks_ago, datetime.min.time()))
    period_end_dt = timezone.now()

    # 1. Buscar analistas ativos com suas atribuições
    analysts = User.objects.filter(
        role='analista', 
        ativo=True,
        department__name='NRS Suporte' # Filtro padrão do sistema
    ).prefetch_related(
        Prefetch('store_assignments', queryset=AnalystAssignment.objects.filter(active=True))
    ).order_by('first_name', 'username')
    
    # 2. Buscar TODOS os KPIs existentes do período para esses analistas
    all_kpis = WeeklyVerificationKPI.objects.filter(
        week_start_date__gte=five_weeks_ago,
        week_start_date__lte=start_of_week_today
    )
    kpi_map = {} # (analyst_id, week_start_date) -> kpi
    for kpi in all_kpis:
        kpi_map[(kpi.analyst_id, kpi.week_start_date)] = kpi
        
    # 3. Buscar TODAS as auditorias do período para todos
    all_audits = StoreAudit.objects.filter(
        created_at__gte=period_start_dt,
        created_at__lte=period_end_dt
    ).values('analyst_id', 'store_id', 'created_at')
    
    audit_map = {} # (analyst_id, store_id) -> list of created_at
    for audit in all_audits:
        key = (audit['analyst_id'], audit['store_id'])
        if key not in audit_map:
            audit_map[key] = []
        audit_map[key].append(audit['created_at'])

    # 4. Buscar última auditoria de cada analista (para o campo last_audit_date)
    # Infelizmente o Django não tem um "distinct on" portátil fácil para isso sem Raw SQL em Bancos não-Postgres
    # Mas como o volume de analistas é pequeno (~20), podemos buscar o último de cada ou fazer uma query global
    # Vamos buscar o último de cada para ser seguro e simples.
    last_audits = {
        item['analyst_id']: item['latest']
        for item in StoreAudit.objects.values('analyst_id').annotate(latest=models.Max('created_at'))
    }

    all_analysts_data = []

    for analyst in analysts:
        assignments = list(analyst.store_assignments.all())
        total_assigned = len(assignments)
        assigned_store_ids = [a.store_id for a in assignments]
        
        weeks_data = []
        completed_weeks_count = 0
        goal_met_count = 0
        
        current_iter_date = five_weeks_ago
        for i in range(5):
            is_current = (current_iter_date == start_of_week_today)
            week_kpi = kpi_map.get((analyst.id, current_iter_date))
            
            if week_kpi:
                percentage = float(week_kpi.completion_percentage)
                gm = week_kpi.goal_met
                sv = week_kpi.stores_verified
                ta = week_kpi.total_assigned_stores
            else:
                # Cálculo em tempo real
                week_end = current_iter_date + timedelta(days=6)
                sw_dt = timezone.make_aware(datetime.combine(current_iter_date, datetime.min.time()))
                ew_dt = timezone.make_aware(datetime.combine(week_end, datetime.max.time()))
                
                sv = 0
                for sid in assigned_store_ids:
                    store_audits = audit_map.get((analyst.id, sid), [])
                    if any(sw_dt <= a <= ew_dt for a in store_audits):
                        sv += 1
                
                ta = total_assigned
                percentage = (sv / ta * 100) if ta > 0 else 0
                gm = (sv >= ta) if ta > 0 else False
                
            week_info = {
                'week_number': i + 1,
                'start_date': current_iter_date.strftime('%d/%m'),
                'is_current': is_current,
                'percentage': round(percentage, 1),
                'goal_met': gm,
                'total_assigned': ta,
                'stores_verified': sv
            }
            
            if not is_current:
                completed_weeks_count += 1
                if gm:
                    goal_met_count += 1
                    
            weeks_data.append(week_info)
            current_iter_date += timedelta(weeks=1)
            
        success_rate = (goal_met_count / completed_weeks_count * 100) if completed_weeks_count > 0 else 0
        
        last_audit_dt = last_audits.get(analyst.id)
        
        all_analysts_data.append({
            'analyst': {
                'id': str(analyst.id),
                'name': analyst.get_full_name() or analyst.username,
                'last_audit_date': last_audit_dt.strftime('%d/%m/%Y %H:%M') if last_audit_dt else None
            },
            'weeks': weeks_data,
            'monthly_stats': {
                'total_weeks': len(weeks_data),
                'completed_weeks': goal_met_count,
                'weeks_evaluated': completed_weeks_count,
                'success_rate': round(success_rate, 1)
            }
        })

    # Ordenar por taxa de sucesso (decrescente) e depois por nome
    all_analysts_data.sort(key=lambda x: (x['monthly_stats']['success_rate'], x['analyst']['name']), reverse=True)
    
    return JsonResponse({
        'success': True,
        'analysts': all_analysts_data
    })


@login_required
@require_http_methods(["POST"])
def api_override_daily_quota(request):
    """
    API para permitir que um gestor aumente o limite diário de um analista.
    Isso é feito adicionando lojas à 'extra_quota' do dia.
    """
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
        
    try:
        import json
        from .models import DailyAuditQuota
        
        data = json.loads(request.body)
        analyst_id = data.get('analyst_id')
        store_ids = data.get('store_ids', [])
        
        if not analyst_id:
            return JsonResponse({'success': False, 'error': 'Analista obrigatório'}, status=400)
            
        analyst = get_object_or_404(User, id=analyst_id)
        
        # Obter quota de hoje
        quota = DailyAuditQuota.get_or_create_today(analyst)
        
        # Adicionar quantidade de lojas selecionadas à quota extra
        extra_count = len(store_ids)
        quota.extra_quota += extra_count
        quota.save()
        
        # Forçar recálculo da meta diária
        # O método calculate_daily_target já inclui self.extra_quota
        quota.daily_quota = quota.calculate_daily_target()
        quota.save()
        
        # Enviar mensagem no chat (simulado ou real se houver sistema de chat)
        # Aqui apenas retornamos sucesso
        
        return JsonResponse({
            'success': True,
            'message': f'Limite de {analyst.get_full_name()} aumentado em {extra_count} lojas para hoje.',
            'new_target': quota.daily_quota
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
