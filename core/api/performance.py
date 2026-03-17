from django.db.models import Avg, Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta, date
from ..models import User, Department, IndicadorDesempenho, ObservacaoDesempenho

def get_performance_stats(department, start_date=None, end_date=None):
    """
    Calculates performance statistics for a department within a date range.
    """
    if not start_date:
        today = timezone.localtime().date()
        start_date = today.replace(day=1)
    
    if not end_date:
        end_date = timezone.localtime().date()

    # Base QuerySet
    indicators = IndicadorDesempenho.objects.filter(
        department=department,
        data__range=[start_date, end_date]
    )
    
    # Aggregations
    total_chats = indicators.aggregate(total=Sum('chats'))['total'] or 0
    avg_nps = indicators.aggregate(avg=Avg('nps'))['avg'] or 0.0
    avg_tme = indicators.aggregate(avg=Avg('tme'))['avg'] or 0
    
    # Ranking by NPS
    ranking = User.objects.filter(
        department=department, 
        role='analista', 
        ativo=True
    ).annotate(
        avg_nps=Avg('indicadores_desempenho__nps', filter=Q(indicadores_desempenho__data__range=[start_date, end_date])),
        total_chats=Sum('indicadores_desempenho__chats', filter=Q(indicadores_desempenho__data__range=[start_date, end_date])),
        avg_tme=Avg('indicadores_desempenho__tme', filter=Q(indicadores_desempenho__data__range=[start_date, end_date]))
    ).order_by(F('avg_nps').desc(nulls_last=True))

    return {
        'total_chats': total_chats,
        'avg_nps': round(avg_nps, 2),
        'avg_tme': int(avg_tme),
        'ranking': ranking,
        'start_date': start_date,
        'end_date': end_date
    }

def get_analyst_history(user, days=30):
    end_date = timezone.localtime().date()
    start_date = end_date - timedelta(days=days)
    
    history = IndicadorDesempenho.objects.filter(
        analista=user,
        data__range=[start_date, end_date]
    ).order_by('data')
    
    observations = ObservacaoDesempenho.objects.filter(
        analista=user,
        data__range=[start_date, end_date]
    ).order_by('-data')
    
    return {
        'history': history,
        'observations': observations
    }

def add_performance_observation(analista, autor, data, texto, tipo, department):
    return ObservacaoDesempenho.objects.create(
        analista=analista,
        autor=autor,
        data=data,
        texto=texto,
        tipo=tipo,
        department=department
    )
