from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import Complaint

@login_required
def reports_view(request):
    """Página de relatórios e estatísticas avançadas"""
    
    # Filtro base por departamento
    if request.user.is_administrador():
        base_queryset = Complaint.objects.all()
    else:
        base_queryset = Complaint.objects.filter(department=request.user.department)

    # Filtros de data
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    complaints = base_queryset
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            complaints = complaints.filter(data_reclamacao__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            complaints = complaints.filter(data_reclamacao__lte=date_to_obj)
        except:
            pass
    
    # Estatísticas gerais
    total = complaints.count()
    by_status = complaints.values('status').annotate(count=Count('id'))
    by_tipo = complaints.values('tipo_reclamacao').annotate(count=Count('id')).exclude(tipo_reclamacao__isnull=True)
    
    # Estatísticas por analista
    by_analyst = complaints.filter(analista__isnull=False).values(
        'analista__username', 'analista__first_name', 'analista__last_name'
    ).annotate(
        total=Count('id'),
        resolvidas=Count('id', filter=Q(status='resolvido')),
        pendentes=Count('id', filter=Q(status='pendente')),
        em_replica=Count('id', filter=Q(status='em_replica')),
        media_nota=Avg('nota_satisfacao')
    ).order_by('-total')
    
    # Estatísticas por loja
    by_store = complaints.values('loja_cod').annotate(
        total=Count('id'),
        resolvidas=Count('id', filter=Q(status='resolvido')),
        media_nota=Avg('nota_satisfacao')
    ).order_by('-total')[:20]
    
    # Satisfação do cliente
    satisfacao_stats = {
        'total_avaliacoes': complaints.filter(nota_satisfacao__isnull=False).count(),
        'media_geral': complaints.aggregate(avg=Avg('nota_satisfacao'))['avg'] or 0,
        'voltaria_sim': complaints.filter(volta_fazer_negocio='sim').count(),
        'voltaria_nao': complaints.filter(volta_fazer_negocio='nao').count(),
    }
    
    # Reclamações por período (últimos 30 dias) - Otimizado
    complaints_by_day = []
    days = 30
    date_threshold = timezone.now().date() - timedelta(days=days)
    
    daily_counts = complaints.filter(
        data_reclamacao__gte=date_threshold
    ).values('data_reclamacao').annotate(count=Count('id'))
    
    counts_map = {item['data_reclamacao']: item['count'] for item in daily_counts if item['data_reclamacao']}
    
    for i in range(days):
        date = timezone.now().date() - timedelta(days=days-1-i)
        count = counts_map.get(date, 0)
        complaints_by_day.append({'date': date.isoformat(), 'count': count})
    
    # Top problemas
    top_problemas = complaints.values('tipo_reclamacao').annotate(
        count=Count('id')
    ).exclude(tipo_reclamacao__isnull=True).order_by('-count')[:10]
    
    context = {
        'total': total,
        'by_status': by_status,
        'by_tipo': by_tipo,
        'by_analyst': by_analyst,
        'by_store': by_store,
        'satisfacao_stats': satisfacao_stats,
        'complaints_by_day': complaints_by_day,
        'top_problemas': top_problemas,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/reports.html', context)
