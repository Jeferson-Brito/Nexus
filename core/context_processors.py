from .models import Department

def departments(request):
    if not request.user.is_authenticated:
        return {}

    # OTIMIZAÇÃO: Para não-admins, usar o departamento já carregado no objeto User
    # sem bater no banco novamente.
    if not request.user.is_administrador():
        selected_dept = request.user.department
        all_depts = [selected_dept] if selected_dept else []
        return {
            'all_departments': all_depts,
            'current_department': selected_dept
        }

    # Para Admins: buscar todos os departamentos (necessário para o seletor do sidebar)
    # Usar cache de sessão para evitar queries em cascata quando admin navega entre páginas.
    all_depts_ids = request.session.get('_all_depts_ids')
    if all_depts_ids is None:
        all_depts = list(Department.objects.filter(show_in_nav=True).order_by('name'))
        request.session['_all_depts_ids'] = [d.id for d in all_depts]
        # Guardar também no atributo da request para reutilização dentro da mesma request
        request._cached_all_depts = all_depts
    else:
        # Carregar apenas se não estiver na memória da request
        if not hasattr(request, '_cached_all_depts'):
            all_depts = list(Department.objects.filter(show_in_nav=True).order_by('name'))
            request._cached_all_depts = all_depts
        all_depts = request._cached_all_depts

    selected_dept = None
    selected_dept_id = request.session.get('selected_department_id')

    if selected_dept_id:
        selected_dept = next((d for d in all_depts if d.id == int(selected_dept_id)), None)

    # Se não houver depto na sessão, buscar o 'NRS Suporte' como padrão
    if not selected_dept:
        nrs_dept = next((d for d in all_depts if d.name == 'NRS Suporte'), None)
        if nrs_dept:
            selected_dept = nrs_dept
            request.session['selected_department_id'] = nrs_dept.id

    return {
        'all_departments': all_depts,
        'current_department': selected_dept
    }
