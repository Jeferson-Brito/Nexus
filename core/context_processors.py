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

    # Para Admins: buscar todos os departamentos marcados para exibição no menu
    # Usar cache apenas na memória da request para evitar queries repetidas na mesma renderização
    if not hasattr(request, '_cached_all_depts'):
        request._cached_all_depts = list(Department.objects.filter(show_in_nav=True).order_by('name'))
    
    all_depts = request._cached_all_depts

    selected_dept = None
    selected_dept_id = request.session.get('selected_department_id')

    if selected_dept_id:
        try:
            # Tentar encontrar o depto selecionado na lista permitida
            selected_dept = next((d for d in all_depts if d.id == int(selected_dept_id)), None)
        except (ValueError, TypeError):
            selected_dept = None

    # Se não houver depto válido selecionado, buscar o 'NRS Suporte' ou o primeiro da lista
    if not selected_dept and all_depts:
        selected_dept = next((d for d in all_depts if d.name == 'NRS Suporte'), all_depts[0])
        if selected_dept:
            request.session['selected_department_id'] = selected_dept.id

    return {
        'all_departments': all_depts,
        'current_department': selected_dept
    }
