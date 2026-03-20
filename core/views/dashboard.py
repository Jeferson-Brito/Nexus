from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from ..models import Complaint, User, Department, AuditLog

@login_required
def change_department(request, dept_id):
    if not request.user.is_administrador():
        return redirect('dashboard')
    
    # dept_id == 0 (Global) removido conforme solicitação
    if dept_id == 0:
        return redirect('dashboard')

    request.session['selected_department_id'] = dept_id
    dept = get_object_or_404(Department, id=dept_id)
    messages.success(request, f"Departamento alterado para: {dept.name}")
    
    # Redirecionar para a página principal de cada departamento
    if dept.name == 'NRS Suporte' or dept.name == 'RH' or dept.name == 'NRP':
        return redirect('escala')
    elif dept.name == 'CS Clientes':
        return redirect('dashboard')
    elif dept.name == 'Onboarding':
        return redirect('onboarding_dev_1')
    
    return redirect('dashboard')

@login_required
def dashboard(request):
    # Identificar o departamento atual (da sessão para admins, do usuário para outros)
    selected_dept_id = request.session.get('selected_department_id')
    
    current_dept = None
    if request.user.is_administrador() and selected_dept_id:
        current_dept = Department.objects.filter(id=selected_dept_id).first()
    elif request.user.department:
        current_dept = request.user.department

    # Redirecionamentos para departamentos com módulos próprios
    if current_dept:
        if current_dept.name in ['NRS Suporte', 'RH', 'NRP']:
            return redirect('escala')
        if current_dept.name == 'Onboarding':
            return redirect('onboarding_dev_1')
    
    # Se não houver depto OU se o depto não for o 'CS Clientes' (único que usa o dashboard de RA atualmente)
    # ou se for explicitamente um depto sem módulo, mostrar tela de Boas-vindas
    active_dashboard_depts = ['CS Clientes', 'Reclame Aqui']
    if not current_dept or (current_dept.name not in active_dashboard_depts):
        return render(request, 'core/welcome.html', {'current_department': current_dept})

    # Se chegou aqui, é CS Clientes ou Reclame Aqui -> Mostrar Dashboard de Reclamações
    dept_id = current_dept.id if current_dept else 0
    cache_key = f'dashboard:stats:dept_{dept_id}'
    
    context = cache.get(cache_key)
    
    if not context:
        queryset = Complaint.objects.filter(department=current_dept)
            
        # OTIMIZAÇÃO: Usar aggregate para buscar contadores em uma única query
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pendente')),
            em_replica=Count('id', filter=Q(status='em_replica')),
            resolved=Count('id', filter=Q(status='resolvido')),
            awaiting=Count('id', filter=Q(status='aguardando_avaliacao')),
            em_andamento=Count('id', filter=Q(status='em_andamento'))
        )

        total_complaints = stats['total']
        pending = stats['pending']
        em_replica = stats['em_replica']
        resolved = stats['resolved']
        awaiting = stats['awaiting']
        em_andamento = stats['em_andamento']
        
        # Ranking de lojas com mais reclamações (top 5)
        top_stores_ranking = queryset.values('loja_cod').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Gráficos
        days = 30
        date_threshold = timezone.now().date() - timedelta(days=days)
        
        # Query única para agrupar por data
        daily_counts = queryset.filter(
            created_at__date__gte=date_threshold
        ).values('created_at__date').annotate(count=Count('id'))
        
        # Transformar em dicionário para lookup rápido
        counts_map = {item['created_at__date']: item['count'] for item in daily_counts}
        
        complaints_by_period = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=days-1-i)
            count = counts_map.get(date, 0)
            complaints_by_period.append({'day': date.isoformat(), 'count': count})
        
        top_stores = queryset.values('loja_cod').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        satisfaction_by_store = queryset.filter(
            nota_satisfacao__isnull=False
        ).values('loja_cod').annotate(
            avg=Avg('nota_satisfacao')
        )
        
        complaints_by_status = queryset.values('status').annotate(
            count=Count('id')
        )
        
        recent_complaints = queryset.select_related('analista').order_by('-created_at')[:10]
        
        # Estatísticas adicionais
        avg_satisfaction = queryset.filter(nota_satisfacao__isnull=False).aggregate(avg=Avg('nota_satisfacao'))['avg'] or 0
        
        if not request.user.is_administrador():
            total_analysts = User.objects.filter(role='analista', ativo=True, department=request.user.department).count()
        else:
            if selected_dept_id:
                total_analysts = User.objects.filter(role='analista', ativo=True, department_id=selected_dept_id).count()
            else:
                total_analysts = User.objects.filter(role='analista', ativo=True).count()
                
        complaints_without_analyst = queryset.filter(analista__isnull=True).count()
        
        # Reclamações urgentes (pendentes há mais de 3 dias)
        urgent_date = timezone.now().date() - timedelta(days=3)
        urgent_complaints = queryset.filter(
            status='pendente',
            data_reclamacao__lte=urgent_date
        ).count()
        
        context = {
            'total_complaints': total_complaints,
            'pending': pending,
            'em_replica': em_replica,
            'em_andamento': em_andamento,
            'resolved': resolved,
            'awaiting': awaiting,
            'recent_complaints': recent_complaints,
            'top_stores': list(top_stores),
            'top_stores_ranking': list(top_stores_ranking),
            'satisfaction_by_store': list(satisfaction_by_store),
            'complaints_by_status': list(complaints_by_status),
            'avg_satisfaction': round(avg_satisfaction, 1),
            'total_analysts': total_analysts,
            'complaints_without_analyst': complaints_without_analyst,
            'urgent_complaints': urgent_complaints,
            'current_department': current_dept,
        }
        # Salva no cache por 1 hora
        cache.set(cache_key, context, 3600)

    # O current_department pode ter mudado se o cache for global, mas aqui o cache é por dept_id
    # Garantir que o current_dept no contexto seja o correto (opcional, mas seguro)
    context['current_department'] = current_dept
    
    return render(request, 'core/dashboard.html', context)
