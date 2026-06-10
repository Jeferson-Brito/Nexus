from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Q

from ..models import Evento, User

@login_required
def api_eventos_users_list(request):
    """Lista usuários (analistas e gestores) do NRS Suporte para o calendário"""
    # Filtra usuários do departamento 'NRS Suporte' e com papel de analista ou gestor
    # O modelo User usa 'ativo'
    users = User.objects.filter(
        ativo=True,
        acesso_escala=True,
        role__in=['analista', 'gestor']
    ).values('id', 'first_name', 'last_name', 'username').order_by('first_name')

    data = []
    for u in users:
        # Formata o nome para exibição "Nome Sobrenome" ou username se não tiver nome
        full_name = f"{u['first_name']} {u['last_name']}".strip()
        if not full_name:
            full_name = u['username']
        
        data.append({
            'id': u['id'],
            'nome': full_name
        })
    
    return JsonResponse(data, safe=False)

@login_required
def api_eventos_list(request):
    """Lista eventos do calendário"""
    # Filtro base por departamento
    selected_dept_id = request.session.get('selected_department_id')
    
    if request.user.is_administrador():
        if selected_dept_id:
            queryset = Evento.objects.filter(department_id=selected_dept_id)
        else:
            queryset = Evento.objects.all()
    else:
        queryset = Evento.objects.filter(department=request.user.department)

    # Filtros de data (opcionais)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        queryset = queryset.filter(data_inicio__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_inicio__lte=data_fim)

    data = [{
        'id': e.id,
        'titulo': e.titulo,
        'descricao': e.descricao,
        'data_inicio': e.data_inicio.isoformat(),
        'horario': e.horario,
        'tipo': e.tipo,
        'codigo_loja': e.codigo_loja,
        'analista_nome': e.analista_nome,
        'observacao': e.observacao,
        'usuario_id': e.usuario_id
    } for e in queryset]
    
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_evento_create(request):
    """Cria um novo evento"""
    try:
        data = json.loads(request.body)
        
        # O departamento é o selecionado na sessão ou o do usuário
        dept = None
        if request.user.is_administrador():
            selected_dept_id = request.session.get('selected_department_id')
            if selected_dept_id:
                from ..models import Department
                dept = get_object_or_404(Department, id=selected_dept_id)
        else:
            dept = request.user.department
            
        if not dept:
            return JsonResponse({'error': 'Departamento não definido.'}, status=400)

        # Permissão Granular: Se não for gestor/admin, o nome do analista é forçado para o próprio usuário
        is_manager = request.user.role in ['gestor', 'administrador']
        analista_nome = data.get('analista_nome')
        
        if not is_manager:
            analista_nome = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

        # Lógica para "Selecionar Todos"
        if analista_nome == 'Todos os Analistas' and is_manager:
            users_to_assign = User.objects.filter(
                department=request.user.department,
                ativo=True,
                role='analista'
            )
            created_ids = []
            last_event = None
            
            for user_target in users_to_assign:
                specific_analyst_name = f"{user_target.first_name} {user_target.last_name}".strip() or user_target.username
                
                evento = Evento.objects.create(
                    titulo=data.get('titulo'),
                    descricao=data.get('descricao'),
                    data_inicio=data.get('data_inicio'),
                    horario=data.get('horario'),
                    tipo=data.get('tipo', 'agendamento'),
                    codigo_loja=data.get('codigo_loja'),
                    analista_nome=specific_analyst_name,
                    observacao=data.get('observacao'),
                    department=dept,
                    usuario=request.user # Quem criou foi o gestor
                )
                created_ids.append(evento.id)
                last_event = evento
            
            # Retorna o ID do último só para compatibilidade ou lista? 
            # O frontend espera 'id' e 'titulo'. Vamos retornar o último.
            return JsonResponse({
                'status': 'success',
                'id': last_event.id if last_event else 0,
                'titulo': last_event.titulo if last_event else ''
            })

        evento = Evento.objects.create(
            titulo=data.get('titulo'),
            descricao=data.get('descricao'),
            data_inicio=data.get('data_inicio'),
            horario=data.get('horario'),
            tipo=data.get('tipo', 'agendamento'),
            codigo_loja=data.get('codigo_loja'),
            analista_nome=analista_nome,
            observacao=data.get('observacao'),
            department=dept,
            usuario=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'id': evento.id,
            'titulo': evento.titulo
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_evento_detail(request, pk):
    """Detalhes, atualização ou exclusão de um evento"""
    # Filtro base por departamento para segurança
    if request.user.is_administrador() or request.user.role == 'gestor':
        evento = get_object_or_404(Evento, pk=pk)
    else:
        evento = get_object_or_404(Evento, pk=pk, department=request.user.department)

    # Verificação de permissão para alteração/exclusão
    can_manage = (request.user.role in ['gestor', 'administrador']) or (evento.usuario_id == request.user.id)

    if request.method == "GET":
        return JsonResponse({
            'id': evento.id,
            'titulo': evento.titulo,
            'descricao': evento.descricao,
            'data_inicio': evento.data_inicio.isoformat(),
            'horario': evento.horario,
            'tipo': evento.tipo,
            'codigo_loja': evento.codigo_loja,
            'analista_nome': evento.analista_nome,
            'observacao': evento.observacao,
            'usuario_id': evento.usuario_id
        })
    
    elif request.method == "PUT":
        if not can_manage:
            return JsonResponse({'error': 'Você não tem permissão para editar este evento.'}, status=403)
        try:
            data = json.loads(request.body)
            evento.titulo = data.get('titulo', evento.titulo)
            evento.descricao = data.get('descricao', evento.descricao)
            evento.data_inicio = data.get('data_inicio', evento.data_inicio)
            evento.horario = data.get('horario', evento.horario)
            evento.tipo = data.get('tipo', evento.tipo)
            evento.codigo_loja = data.get('codigo_loja', evento.codigo_loja)
            evento.analista_nome = data.get('analista_nome', evento.analista_nome)
            evento.observacao = data.get('observacao', evento.observacao)
            evento.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    elif request.method == "DELETE":
        if not can_manage:
            return JsonResponse({'error': 'Você não tem permissão para excluir este evento.'}, status=403)
        evento.delete()
        return JsonResponse({'status': 'success'})
