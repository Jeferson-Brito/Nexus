from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from ..models import Lista, Cartao, User, Department, QuadroEtiqueta, CartaoComentario, CartaoAnexo
import json
from datetime import datetime

def get_department(request):
    if request.user.is_administrador():
        dept_id = request.session.get('selected_department_id')
        if dept_id and dept_id != 0:
            return Department.objects.filter(id=dept_id).first() or Department.objects.first()
        return Department.objects.first()
    return request.user.department

from django.db.models import Count

@login_required
@require_http_methods(["GET"])
def api_quadro_data(request):
    """Retorna todas as listas e cartões do departamento do usuário"""
    department = get_department(request)
    if not department:
        return JsonResponse({'error': 'Usuário sem departamento'}, status=400)
    
    # Listas
    listas = Lista.objects.filter(department=department, archived=False).order_by('ordem')
    
    # Etiquetas do departamento
    etiquetas = QuadroEtiqueta.objects.filter(department=department)
    etiquetas_data = [{'id': e.id, 'nome': e.nome, 'cor': e.cor} for e in etiquetas]

    # Membros do departamento (para atribuição)
    membros_dept = User.objects.filter(department=department, is_active=True)
    membros_data = [{'id': u.id, 'nome': u.get_full_name() or u.username, 'avatar': None} for u in membros_dept]

    data = []
    
    for lista in listas:
        # OTIMIZAÇÃO: Usar annotate para contar relacionamentos sem carregar objetos
        cartoes = lista.cartoes.filter(archived=False).order_by('ordem').annotate(
            num_comentarios=Count('comentarios'),
            num_anexos=Count('anexos')
        ).prefetch_related('membros', 'etiquetas')
        
        cartoes_data = []
        for cartao in cartoes:
            cartoes_data.append({
                'id': cartao.id,
                'titulo': cartao.titulo,
                'descricao': cartao.descricao,
                'prioridade': cartao.prioridade,
                'data_limite': cartao.data_limite.strftime('%Y-%m-%d') if cartao.data_limite else None,
                # Legacy responsavel fallback
                'responsavel_id': cartao.responsavel.id if cartao.responsavel else None,
                'membros': [{'id': m.id, 'nome': m.get_full_name() or m.username} for m in cartao.membros.all()],
                'etiquetas': [{'id': e.id, 'nome': e.nome, 'cor': e.cor} for e in cartao.etiquetas.all()],
                'checklists': cartao.checklists,
                'cover_color': cartao.cover_color,
                'comentarios_count': cartao.num_comentarios,
                'anexos_count': cartao.num_anexos,
            })
            
        data.append({
            'id': lista.id,
            'titulo': lista.titulo,
            'cartoes': cartoes_data
        })
        
    return JsonResponse({
        'listas': data,
        'etiquetas_disponiveis': etiquetas_data,
        'membros_disponiveis': membros_data
    })

@login_required
@require_http_methods(["GET"])
def api_cartao_details(request, cartao_id):
    """Retorna detalhes completos de um cartão (comentários, anexos, etc)"""
    try:
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        
        comentarios = []
        for c in cartao.comentarios.all().order_by('-created_at'):
            comentarios.append({
                'id': c.id,
                'usuario': c.usuario.get_full_name() or c.usuario.username,
                'texto': c.texto,
                'created_at': c.created_at.strftime('%d/%m %H:%M')
            })

        anexos = []
        for a in cartao.anexos.all():
            anexos.append({
                'id': a.id,
                'nome': a.nome_original,
                'url': a.arquivo.url,
                'uploaded_at': a.uploaded_at.strftime('%d/%m %H:%M')
            })

        return JsonResponse({
            'id': cartao.id,
            'titulo': cartao.titulo,
            'descricao': cartao.descricao or '',
            'prioridade': cartao.prioridade or 'baixa',
            'data_limite': cartao.data_limite.strftime('%Y-%m-%d') if cartao.data_limite else '',
            'comentarios': comentarios,
            'anexos': anexos
        })
    except Cartao.DoesNotExist:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)

@login_required
@require_http_methods(["POST"])
def api_cartao_create(request):
    """Cria um novo cartão"""
    try:
        data = json.loads(request.body)
        lista_id = data.get('lista_id')
        titulo = data.get('titulo')
        
        if not lista_id or not titulo:
            return JsonResponse({'error': 'Dados incompletos'}, status=400)
            
        department = get_department(request)
        lista = Lista.objects.get(id=lista_id, department=department)
        ultima_ordem = lista.cartoes.count()
        
        cartao = Cartao.objects.create(
            titulo=titulo,
            lista=lista,
            department=department,
            criado_por=request.user,
            ordem=ultima_ordem
        )
        
        return JsonResponse({'id': cartao.id, 'titulo': cartao.titulo})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_cartao_update(request, cartao_id):
    """Atualiza cartão"""
    try:
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        data = json.loads(request.body)
        
        if 'titulo' in data: 
            cartao.titulo = data['titulo']
            log_activity(cartao, request.user, f"alterou o título para '{data['titulo']}'")
        if 'descricao' in data: 
            cartao.descricao = data['descricao']
            # Description change too verbose to log every character, maybe only significant saves?
            
        if 'cover_color' in data: cartao.cover_color = data['cover_color']
        
        if 'membros' in data:
            cartao.membros.set(User.objects.filter(id__in=data['membros']))
            log_activity(cartao, request.user, "atualizou os membros")
            
        if 'etiquetas' in data:
            cartao.etiquetas.set(QuadroEtiqueta.objects.filter(id__in=data['etiquetas']))

        if 'checklists' in data:
            cartao.checklists = data['checklists']

        if 'data_limite' in data:
             cartao.data_limite = datetime.strptime(data['data_limite'], '%Y-%m-%d').date() if data['data_limite'] else None
             log_activity(cartao, request.user, f"definiu data limite para {data['data_limite']}")

        cartao.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_cartao_move(request):
    """Move cartão"""
    try:
        data = json.loads(request.body)
        cartao_id = data.get('cartao_id')
        nova_lista_id = data.get('nova_lista_id')
        nova_posicao = data.get('nova_posicao', 0)
        
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        lista_destino = Lista.objects.get(id=nova_lista_id, department=department)
        
        if cartao.lista.id != lista_destino.id:
            old_list = cartao.lista.titulo
            cartao.lista = lista_destino
            log_activity(cartao, request.user, f"moveu este cartão de '{old_list}' para '{lista_destino.titulo}'")
            
        # Reordenação simplificada
        cartoes_destino = list(lista_destino.cartoes.exclude(id=cartao.id).order_by('ordem'))
        if nova_posicao > len(cartoes_destino): nova_posicao = len(cartoes_destino)
        cartoes_destino.insert(int(nova_posicao), cartao)
        
        for index, c in enumerate(cartoes_destino):
            c.ordem = index
            c.save()
            
        return JsonResponse({'success': True})
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["DELETE"])
def api_cartao_delete(request, cartao_id):
    try:
        department = get_department(request)
        Cartao.objects.get(id=cartao_id, department=department).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# NOVOS ENDPOINTS

@login_required
@require_http_methods(["POST"])
def api_comentario_add(request, cartao_id):
    try:
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        data = json.loads(request.body)
        
        comentario = CartaoComentario.objects.create(
            cartao=cartao,
            usuario=request.user,
            texto=data.get('texto')
        )
        return JsonResponse({
            'id': comentario.id, 
            'usuario': request.user.get_full_name() or request.user.username,
            'texto': comentario.texto,
            'created_at': comentario.created_at.strftime('%d/%m %H:%M')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_lista_create(request):
    try:
        data = json.loads(request.body)
        department = get_department(request)
        ordem = Lista.objects.filter(department=department).count()
        lista = Lista.objects.create(
            titulo=data.get('titulo', 'Nova Lista'),
            department=department,
            ordem=ordem
        )
        return JsonResponse({'id': lista.id, 'titulo': lista.titulo, 'cartoes': []})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["DELETE"])
def api_lista_delete(request, lista_id):
    try:
        department = get_department(request)
        Lista.objects.get(id=lista_id, department=department).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_anexo_add(request, cartao_id):
    try:
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        
        if 'arquivo' not in request.FILES:
            return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)
            
        arquivo = request.FILES['arquivo']
        anexo = CartaoAnexo.objects.create(
            cartao=cartao,
            usuario=request.user,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tipo_arquivo=arquivo.content_type,
            tamanho=arquivo.size
        )
        
        return JsonResponse({
            'id': anexo.id,
            'nome': anexo.nome_original,
            'url': anexo.arquivo.url,
            'uploaded_at': anexo.uploaded_at.strftime('%d/%m %H:%M')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["DELETE"])
def api_anexo_delete(request, anexo_id):
    try:
        department = get_department(request)
        # Verify access via card->department
        anexo = CartaoAnexo.objects.get(id=anexo_id, cartao__department=department)
        anexo.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_lista_move(request):
    """Reordena listas"""
    try:
        data = json.loads(request.body)
        lista_id = data.get('lista_id')
        nova_posicao = data.get('nova_posicao', 0)
        
        department = get_department(request)
        lista = Lista.objects.get(id=lista_id, department=department)
        
        # Reordenação
        listas = list(Lista.objects.filter(department=department, archived=False).exclude(id=lista_id).order_by('ordem'))
        if nova_posicao > len(listas): nova_posicao = len(listas)
        listas.insert(int(nova_posicao), lista)
        
        for index, l in enumerate(listas):
            l.ordem = index
            l.save()
            
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_cartao_archive(request, cartao_id):
    try:
        department = get_department(request)
        cartao = Cartao.objects.get(id=cartao_id, department=department)
        cartao.archived = True
        cartao.save()
        log_activity(cartao, request.user, "arquivou este cartão")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_lista_archive(request, lista_id):
    try:
        department = get_department(request)
        lista = Lista.objects.get(id=lista_id, department=department)
        lista.archived = True
        lista.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
