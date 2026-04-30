from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import authenticate
from ..models import User, Department, AuditLog
from collections import defaultdict

@login_required
def user_list(request):
    """Lista de usuários - apenas para gestores e administradores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para ver a lista de usuários.')
        return redirect('dashboard')
    
    departments = Department.objects.all().order_by('name')
    
    # Filtro base por departamento
    if request.user.is_administrador():
        users = User.objects.all().order_by('first_name', 'username')
    else:
        # Gestor só vê usuários do seu departamento
        users = User.objects.filter(department=request.user.department).order_by('first_name', 'username')
    
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    dept_filter = request.GET.get('department', '')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if dept_filter:
        users = users.filter(department_id=dept_filter)
    
    if status_filter == 'ativo':
        users = users.filter(ativo=True)
    elif status_filter == 'inativo':
        users = users.filter(ativo=False)
    
    paginator = Paginator(users, 10)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    context = {
        'users': users,
        'departments': departments
    }
    
    return render(request, 'core/user_list.html', context)

@login_required
def user_create(request):
    """Criar novo usuário - apenas para gestores e administradores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para criar usuários.')
        return redirect('dashboard')
    
    departments = Department.objects.all()
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'analista')
        department_id = request.POST.get('department')
        ativo = request.POST.get('is_active') == 'on'
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        profile_photo = request.FILES.get('profile_photo')
        
        # Restrições de Gestor
        if request.user.is_gestor() and not request.user.is_administrador():
            role = 'analista'
            department_id = str(request.user.department_id) if request.user.department_id else None
            
        department = None
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
            except (Department.DoesNotExist, ValueError):
                department = None
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este nome de usuário já existe.')
            return render(request, 'core/user_form.html', {
                'form_type': 'create',
                'departments': departments,
                'form_data': {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': role,
                    'ativo': ativo,
                    'department_id': department_id
                }
            })
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está cadastrado.')
            return render(request, 'core/user_form.html', {
                'form_type': 'create',
                'departments': departments,
                'form_data': {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': role,
                    'ativo': ativo,
                    'department_id': department_id
                }
            })
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            department=department,
            ativo=ativo,
            first_name=first_name,
            last_name=last_name
        )
        
        if profile_photo:
            user.profile_photo = profile_photo
            user.save()

        # Integração Escala NRS Suporte
        if role == 'analista' and department and department.name == 'NRS Suporte':
            try:
                from ..models import AnalistaEscala
                formatted_name = AnalistaEscala.format_schedule_name(first_name, last_name)
                AnalistaEscala.objects.create(
                    user=user,
                    nome=formatted_name,
                    ativo=ativo
                )
            except Exception as e:
                print(f"Erro ao criar AnalistaEscala para {username}: {e}")
        
        AuditLog.objects.create(
            usuario=request.user,
            action='create',
            target_type='User',
            target_id=user.id,
            detalhes_json={'username': username, 'role': role}
        )
        
        messages.success(request, f'Usuário {username} criado com sucesso!')
        return redirect('user_list')
    
    return render(request, 'core/user_form.html', {
        'form_type': 'create',
        'departments': departments,
        'form_data': defaultdict(str)
    })

@login_required
def user_edit(request, pk):
    """Editar usuário - apenas para gestores e administradores"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para editar usuários.')
        return redirect('dashboard')
    
    departments = Department.objects.all()
    user_to_edit = get_object_or_404(User, pk=pk)
    
    if request.user.is_gestor():
        if user_to_edit != request.user:
            if user_to_edit.department != request.user.department or user_to_edit.role != 'analista':
                messages.error(request, 'Você não tem permissão para editar este usuário.')
                return redirect('user_list')
    
    if request.method == 'POST':
        user_to_edit.email = request.POST.get('email')
        role = request.POST.get('role')
        department_id = request.POST.get('department')
        if department_id:
            department_id = str(department_id).replace('.', '').replace(',', '').strip()
            
        profile_photo = request.FILES.get('profile_photo')
        
        if request.user.is_administrador():
            user_to_edit.role = role
            if department_id:
                try:
                    user_to_edit.department = Department.objects.get(id=department_id)
                except (Department.DoesNotExist, ValueError):
                    user_to_edit.department = None
            else:
                user_to_edit.department = None
        elif request.user.is_gestor():
            user_to_edit.department = request.user.department
        
        user_to_edit.ativo = request.POST.get('is_active') == 'on'
        user_to_edit.first_name = request.POST.get('first_name', '')
        user_to_edit.last_name = request.POST.get('last_name', '')
        
        if profile_photo:
            user_to_edit.profile_photo = profile_photo
        
        password = request.POST.get('password')
        if password:
            user_to_edit.set_password(password)
            
        user_to_edit.save()
        
        # Sincronização Escala NRS Suporte
        try:
            if hasattr(user_to_edit, 'escala_perfil'):
                analista_escala = user_to_edit.escala_perfil
                if not user_to_edit.department or user_to_edit.department.name != 'NRS Suporte':
                    analista_escala.ativo = False
                else:
                    from ..models import AnalistaEscala
                    analista_escala.nome = AnalistaEscala.format_schedule_name(user_to_edit.first_name, user_to_edit.last_name)
                    analista_escala.ativo = user_to_edit.ativo
                analista_escala.save()
        except Exception as e:
            print(f"Erro ao sincronizar AnalistaEscala para {user_to_edit.username}: {e}")
        
        AuditLog.objects.create(
            usuario=request.user,
            action='update',
            target_type='User',
            target_id=user_to_edit.id,
            detalhes_json={'username': user_to_edit.username, 'role': user_to_edit.role}
        )
        
        messages.success(request, f'Usuário {user_to_edit.username} atualizado!')
        return redirect('user_list')
    
    return render(request, 'core/user_form.html', {
        'form_type': 'edit',
        'target_user': user_to_edit,
        'departments': departments,
        'form_data': defaultdict(str)
    })

@login_required
def user_delete(request, pk):
    """Excluir usuário - apenas para gestores e administradores (requer POST)"""
    if not (request.user.is_gestor() or request.user.is_administrador()):
        messages.error(request, 'Você não tem permissão para excluir usuários.')
        return redirect('user_list')

    # Exige confirmação via POST (enviado pelo SweetAlert2 no frontend)
    if request.method != 'POST':
        return redirect('user_list')

    user_to_delete = get_object_or_404(User, pk=pk)

    if request.user.is_gestor():
        if user_to_delete.department != request.user.department or user_to_delete.role != 'analista':
            messages.error(request, 'Você não tem permissão para excluir este usuário.')
            return redirect('user_list')

    if user_to_delete.id == request.user.id:
        messages.error(request, 'Você não pode excluir sua própria conta.')
        return redirect('user_list')

    username = user_to_delete.username
    user_to_delete.delete()

    AuditLog.objects.create(
        usuario=request.user,
        action='delete',
        target_type='User',
        target_id=pk,
        detalhes_json={'username': username}
    )

    messages.success(request, f'Usuário {username} excluído!')
    return redirect('user_list')
