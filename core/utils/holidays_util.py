import holidays
from django.utils import timezone
from datetime import date
from core.models import Holiday

def get_all_holidays(start_year, end_year):
    """
    Retorna a lista unificada de feriados do banco de dados (locais) 
    e os feriados nacionais dinâmicos calculados pela biblioteca holidays.
    """
    # 1. Calcular Feriados Dinâmicos (Naturais do Brasil - Federais) via biblioteca
    br_holidays = {}
    nat_dates = set()
    nat_annual_days = set()
    
    if start_year and end_year:
        br_holidays = holidays.country_holidays('BR', years=range(start_year, end_year + 1), language='pt_BR')
        nat_dates = set(br_holidays.keys())
        nat_annual_days = {(dt.month, dt.day) for dt in nat_dates}
        
    # 2. Feriados do Banco (Locais e fixados manualmente)
    db_holidays = Holiday.objects.all().order_by('date')
    
    feriados_lista = []
    
    # Adicionar os do BD na lista resultante
    for f in db_holidays:
        is_nat = False
        if not f.repeats_annually and f.date in nat_dates:
            is_nat = True
        elif f.repeats_annually and (f.date.month, f.date.day) in nat_annual_days:
            is_nat = True
            
        feriados_lista.append({
            'source': 'db',
            'id': str(f.id),
            'name': f.name,
            'date': f.date,
            'date_iso': f.date.isoformat(),
            'date_display': f.date.strftime('%d/%m/%Y') if not f.repeats_annually else f.date.strftime('%d/%m'),
            'repeats_annually': f.repeats_annually,
            'apply_to_all': f.apply_to_all,
            'target_companies': list(f.target_companies.values_list('id', flat=True)) if not f.apply_to_all else [],
            'target_departments': list(f.target_departments.values_list('id', flat=True)) if not f.apply_to_all else [],
            'target_turnos': list(f.target_turnos.values_list('id', flat=True)) if not f.apply_to_all else [],
            'is_national': is_nat,
            'can_delete': True,
        })
        
    # Mapeamentos para evitar duplicacao com feriados nacionais ja criados manualmente
    db_dates_set = {f['date'] for f in feriados_lista if not f['repeats_annually']}
    db_annual_days_set = {(f['date'].month, f['date'].day) for f in feriados_lista if f['repeats_annually']}
    
    # 3. Adicionar Feriados Dinâmicos que não foram sobrepostos
    for dt, name in br_holidays.items():
        if dt in db_dates_set or (dt.month, dt.day) in db_annual_days_set:
            continue
            
        feriados_lista.append({
            'source': 'national',
            'id': f'NAT_{dt.isoformat()}',
            'name': name,
            'date': dt,
            'date_iso': dt.isoformat(),
            'date_display': dt.strftime('%d/%m/%Y'),
            'repeats_annually': False,
            'apply_to_all': True,
            'target_companies': [],
            'target_departments': [],
            'target_turnos': [],
            'is_national': True,
            'can_delete': False,
        })
            
    # Ordenar tudo pela data
    feriados_lista.sort(key=lambda x: (x['date'].month, x['date'].day) if x['repeats_annually'] else (x['date'].year, x['date'].month, x['date'].day))
    
    return feriados_lista
