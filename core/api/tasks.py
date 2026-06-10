from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
from datetime import datetime, timedelta, date

from ..models import Task, Routine, RoutineLog, User

@login_required
def api_tasks_list(request):
    """Lista tarefas pendentes e concluídas do usuário ou do time (se gestor)"""
    user = request.user
    
    # Filtros
    filter_type = request.GET.get('type') # 'my' or 'team'
    
    if filter_type == 'team' and (user.is_gestor() or user.is_administrador()):
        if user.is_administrador():
            selected_dept_id = request.session.get('selected_department_id')
            if selected_dept_id:
                tasks = Task.objects.filter(assigned_to__department_id=selected_dept_id)
            else:
                 # Se nenhum departamento selecionado, mostra tudo ou nada?
                 # Pela lógica do base.html, se não tem selecionado, é Global (Todos)
                 tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(assigned_to__department=user.department)
        
        tasks = tasks.select_related('assigned_to', 'created_by').order_by('due_date', '-priority')
    else:
        tasks = Task.objects.filter(assigned_to=user).select_related('assigned_to', 'created_by').order_by('due_date', '-priority')

    data = [{
        'id': str(t.id),
        'title': t.title,
        'description': t.description,
        'assigned_to': f"{t.assigned_to.first_name} {t.assigned_to.last_name}" if t.assigned_to.first_name else t.assigned_to.username,
        'assigned_to_id': str(t.assigned_to.id),
        'created_by': t.created_by.username,
        'due_date': t.due_date.isoformat() if t.due_date else None,
        'priority': t.priority,
        'status': t.status,
    } for t in tasks]
    
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_task_create(request):
    """Cria uma nova tarefa"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Apenas gestores podem criar tarefas.'}, status=403)
        
    try:
        data = json.loads(request.body)
        assigned_to_id = data.get('assigned_to_id')
        
        # Lógica para "Selecionar Todos"
        users_to_assign = []
        if assigned_to_id == 'all':
            dept_to_filter = request.user.department
            if request.user.is_administrador():
                selected_dept_id = request.session.get('selected_department_id')
                if selected_dept_id:
                    # Necessário importar Department se fosse objeto, mas filter por id funciona
                    dept_to_filter = selected_dept_id
                else:
                    dept_to_filter = None # Global? Perigoso atribuir a TODOS do sistema.
            
            if dept_to_filter:
                # Busca todos usuários ativos do departamento
                users_to_assign = User.objects.filter(
                    department_id=dept_to_filter if request.user.is_administrador() else dept_to_filter.id,
                    ativo=True,
                    role='analista'
                )
            elif request.user.is_administrador() and not dept_to_filter:
                # Se admin e global, pega todos analistas do sistema?
                users_to_assign = User.objects.filter(ativo=True, role='analista')

        else:
            users_to_assign = [get_object_or_404(User, pk=assigned_to_id)]

        created_ids = []
        for user_target in users_to_assign:
            # Simple handling of due_date string, strictly assuming ISO format or similar
            # if provided. Django usually handles ISO strings.
            d_date = data.get('due_date')
            
            task = Task.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                assigned_to=user_target,
                created_by=request.user,
                due_date=d_date,
                priority=data.get('priority', 'media'),
                status='pendente'
            )
            created_ids.append(task.id)
        
        return JsonResponse({'ids': [str(x) for x in created_ids], 'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_task_edit(request, pk):
    """Edita uma tarefa existente (apenas gestores/admins)"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Permissão negada.'}, status=403)
        
    task = get_object_or_404(Task, pk=pk)
    
    try:
        data = json.loads(request.body)
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.due_date = data.get('due_date', task.due_date)
        task.priority = data.get('priority', task.priority)
        # Allows changing assignee? Maybe. For now keeps simple.
        task.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_task_toggle(request, pk):
    """Marca tarefa como concluída/pendente"""
    task = get_object_or_404(Task, pk=pk)
    
    # Apenas o dono ou gestor pode alterar
    if task.assigned_to != request.user and not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Sem permissão.'}, status=403)
        
    data = json.loads(request.body)
    completed = data.get('completed', False)
    
    if completed:
        task.status = 'concluida'
        task.completed_at = timezone.now()
    else:
        task.status = 'pendente'
        task.completed_at = None
        
    task.save()
    return JsonResponse({'status': 'success', 'new_status': task.status})

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def api_task_delete(request, pk):
    """Exclui uma tarefa (apenas gestores/admins)"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Apenas gestores e administradores podem excluir tarefas.'}, status=403)
    
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    return JsonResponse({'status': 'success', 'message': 'Tarefa excluída com sucesso.'})

# --- ROTINAS ---

@login_required
def api_routines_daily(request):
    """
    Retorna checklist de rotinas do dia para o usuário.
    Gera automaticamente os logs do dia se não existirem.
    """
    user = request.user
    today = timezone.localtime().date()
    
    # Busca todas as rotinas ativas para o usuário
    routines = Routine.objects.filter(assigned_to=user, active=True)
    
    checklist = []
    
    # Optimize: Fetch existing logs for today to avoid N+1
    existing_logs = {log.routine_id: log for log in RoutineLog.objects.filter(routine__in=routines, date=today)}
    
    # Identify missing logs and bulk create them
    missing_routines = [r for r in routines if r.id not in existing_logs]
    if missing_routines:
        new_logs = [RoutineLog(routine=r, date=today, completed=False) for r in missing_routines]
        RoutineLog.objects.bulk_create(new_logs)
        # Fetch again to get IDs (bulk_create doesn't return IDs on all DBs, but generally safe to re-fetch or use logic)
        # For simplicity and robust ID access, re-fetching is safer or just use the objects if not needing IDs immediately for JSON?
        # We need log.id for the frontend checklist.
        existing_logs = {log.routine_id: log for log in RoutineLog.objects.filter(routine__in=routines, date=today)}

    for r in routines:
        log = existing_logs.get(r.id)
        if log:
            checklist.append({
                'log_id': str(log.id),
                'routine_id': str(r.id),
                'title': r.title,
                'description': r.description,
                'completed': log.completed
            })
        
    return JsonResponse(checklist, safe=False)

@login_required
def api_routines_overview(request):
    """
    Retorna o status das rotinas de TODOS os analistas para o dia atual.
    Apenas para gestores.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    today = timezone.localtime().date()
    
    dept_to_filter = request.user.department
    if request.user.is_administrador():
        selected_dept_id = request.session.get('selected_department_id')
        if selected_dept_id:
            dept_to_filter = selected_dept_id
        else:
            dept_to_filter = None

    # Busca todos os analistas do departamento
    if dept_to_filter:
        analysts = User.objects.filter(
            department_id=dept_to_filter if request.user.is_administrador() else dept_to_filter.id,
            ativo=True,
            role='analista'
        ).order_by('first_name')
    elif request.user.is_administrador():
        analysts = User.objects.filter(ativo=True, role='analista').order_by('first_name')
    else:
        analysts = []

    overview = []
    
    for analyst in analysts:
        # Busca routines do analista
        routines = Routine.objects.filter(assigned_to=analyst, active=True)
        analyst_data = {
            'analyst_name': f"{analyst.first_name} {analyst.last_name}".strip() or analyst.username,
            'analyst_id': str(analyst.id),
            'routines': []
        }
        
        for r in routines:
            # Check log status without creating if easy, but creating ensures consistency
            log, _ = RoutineLog.objects.get_or_create(
                routine=r,
                date=today,
                defaults={'completed': False}
            )
            analyst_data['routines'].append({
                'title': r.title,
                'completed': log.completed
            })
            
        overview.append(analyst_data)
        
    return JsonResponse(overview, safe=False)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_routine_check(request, log_id):
    """Marca uma rotina diária como feta"""
    log = get_object_or_404(RoutineLog, pk=log_id)
    
    if log.routine.assigned_to != request.user:
        return JsonResponse({'error': 'Sem permissão.'}, status=403)
        
    data = json.loads(request.body)
    log.completed = data.get('completed', False)
    log.completed_at = timezone.now() if log.completed else None
    log.save()
    
    return JsonResponse({'status': 'success'})

@login_required
def api_manager_alerts(request):
    """
    Retorna alertas para o gestor sobre rotinas não cumpridas ONTEM.
    """
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Acesso negado'}, status=403)
        
    yesterday = timezone.localtime().date() - timedelta(days=1)
    
    # Busca logs de ontem que não foram completados
    # Filtrando por departamento do gestor
    missed_logs = RoutineLog.objects.filter(
        date=yesterday,
        completed=False,
        routine__assigned_to__department=request.user.department
    ).select_related('routine', 'routine__assigned_to')
    
    alerts = []
    for log in missed_logs:
        alerts.append({
            'analyst': f"{log.routine.assigned_to.first_name} {log.routine.assigned_to.last_name}",
            'routine': log.routine.title,
            'date': yesterday.isoformat()
        })
        
    return JsonResponse(alerts, safe=False)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_routine_create(request):
    """Cria uma nova rotina para um analista"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        return JsonResponse({'error': 'Apenas gestores podem criar rotinas.'}, status=403)
        
    try:
        data = json.loads(request.body)
        assigned_to_id = data.get('assigned_to_id')
        
        users_to_assign = []
        if assigned_to_id == 'all':
            dept_to_filter = request.user.department
            if request.user.is_administrador():
                selected_dept_id = request.session.get('selected_department_id')
                if selected_dept_id:
                    dept_to_filter = selected_dept_id
                else:
                    dept_to_filter = None
            
            if dept_to_filter:
                 users_to_assign = User.objects.filter(
                    department_id=dept_to_filter if request.user.is_administrador() else dept_to_filter.id,
                    ativo=True,
                    role='analista'
                )
            elif request.user.is_administrador():
                 users_to_assign = User.objects.filter(ativo=True, role='analista')
        else:
            users_to_assign = [get_object_or_404(User, pk=assigned_to_id)]
        
        created_ids = []
        for user_target in users_to_assign:
            routine = Routine.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                assigned_to=user_target,
                created_by=request.user,
                frequency='diaria', # Por enquanto fixo
                time_limit=data.get('time_limit'), # Expects "HH:MM"
                active=True
            )
            created_ids.append(routine.id)
        
        return JsonResponse({'ids': [str(x) for x in created_ids], 'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_notifications_check(request):
    """
    Verifica novas tarefas/rotinas E alertas de vencimento (10min).
    Retorna lista de notificações.
    """
    user = request.user
    notifications = []
    
    # 1. Novas Tarefas
    new_tasks = Task.objects.filter(assigned_to=user, notified=False)[:50]
    for t in new_tasks:
        notifications.append({
            'type': 'new_task',
            'title': t.title,
            'id': t.id,
            'message': f"Nova tarefa atribuída: {t.title}"
        })
        t.notified = True
        t.save()
        
    # 2. Novas Rotinas
    new_routines = Routine.objects.filter(assigned_to=user, notified=False)[:50]
    for r in new_routines:
        notifications.append({
            'type': 'new_routine',
            'title': r.title,
            'id': r.id,
            'message': f"Nova rotina atribuída: {r.title}"
        })
        r.notified = True
        r.save()
        
    # 3. Alertas de Vencimento de Tarefas (10 min antes)
    now = timezone.now()
    warning_threshold = now + timedelta(minutes=10)
    
    warning_tasks = Task.objects.filter(
        assigned_to=user,
        status='pendente',
        warning_sent=False,
        due_date__isnull=False,
        due_date__gt=now,
        due_date__lte=warning_threshold
    )
    
    for t in warning_tasks:
        notifications.append({
            'type': 'warning_task',
            'title': t.title,
            'id': t.id,
            'message': f"ATENÇÃO: A tarefa '{t.title}' vence em breve!"
        })
        t.warning_sent = True
        t.save()

    # 4. Alertas de Vencimento de Rotinas (10 min antes do time_limit)
    today = timezone.localtime().date()
    timed_routines = Routine.objects.filter(assigned_to=user, active=True, time_limit__isnull=False)
    
    # Bulk check logs
    existing_logs = {log.routine_id: log for log in RoutineLog.objects.filter(routine__in=timed_routines, date=today)}
    
    for r in timed_routines:
        limit_dt = datetime.combine(today, r.time_limit)
        limit_dt = timezone.make_aware(limit_dt)
        
        time_diff = (limit_dt - now).total_seconds()
        
        if 0 < time_diff <= 600:
            log = existing_logs.get(r.id)
            if not log:
                # Create if missing (only if within warning window to save DB space? 
                # Or just create. Better to create to track it.)
                log = RoutineLog.objects.create(routine=r, date=today, completed=False)
                existing_logs[r.id] = log
                
            if not log.completed and not log.warning_sent:
                notifications.append({
                    'type': 'warning_routine',
                    'title': r.title,
                    'id': str(r.id),
                    'message': f"ATENÇÃO: A rotina '{r.title}' deve ser feita até {r.time_limit.strftime('%H:%M')}!"
                })
                log.warning_sent = True
                log.save()
                
    return JsonResponse({'has_notifications': len(notifications) > 0, 'notifications': notifications})
