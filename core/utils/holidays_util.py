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
    nat_names = set()
    
    if start_year and end_year:
        br_holidays = holidays.country_holidays('BR', years=range(start_year, end_year + 1), language='pt_BR')
        nat_names = set(br_holidays.values())
        
    # 2. Feriados do Banco (Locais e fixados manualmente)
    db_holidays = Holiday.objects.all().order_by('date')
    
    feriados_lista = []
    db_overrides = {}
    
    for f in db_holidays:
        if f.name in nat_names:
            # É uma personalização (override) de um feriado nacional!
            # Separamos para aplicar regras diretamente sobre as datas corretas (móveis)
            db_overrides[f.name] = f
        else:
            # É puramente um feriado local
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
                'is_national': False,
                'can_delete': True,
            })
            
    # 3. Adicionar Feriados Dinâmicos aplicando os Overrides locais
    for dt, name in br_holidays.items():
        custom_db = db_overrides.get(name)
        
        if custom_db:
            # Overrides garantem as personalizações corporativas nas datas dinâmicas perfeitas (sem duplicar feriados móveis)
            feriados_lista.append({
                'source': 'national_override',
                'id': str(custom_db.id),
                'name': name,
                'date': dt,
                'date_iso': dt.isoformat(),
                'date_display': dt.strftime('%d/%m/%Y'),
                'repeats_annually': False,
                'apply_to_all': custom_db.apply_to_all,
                'target_companies': list(custom_db.target_companies.values_list('id', flat=True)) if not custom_db.apply_to_all else [],
                'target_departments': list(custom_db.target_departments.values_list('id', flat=True)) if not custom_db.apply_to_all else [],
                'target_turnos': list(custom_db.target_turnos.values_list('id', flat=True)) if not custom_db.apply_to_all else [],
                'is_national': True,
                'can_delete': True,
            })
        else:
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
