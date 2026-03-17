"""
API REST para Kanban Board
Endpoints para gerenciar quadros, listas, cartões, labels, checklists e comentários
"""
import json
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max
from django.utils import timezone

from ..models import (
    User, KanbanBoard, BoardMembership, KanbanList, KanbanCard,
    CardLabel, Checklist, ChecklistItem, CardComment, CardAttachment, CardActivity
)


def api_login_required(view_func):
    """Custom login_required that returns JSON 401 instead of redirect"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper



# ============================================
# HELPER FUNCTIONS
# ============================================

def get_user_boards(user):
    """Retorna quadros que o usuário é dono ou membro"""
    owned = KanbanBoard.objects.filter(owner=user, is_archived=False)
    member_of = KanbanBoard.objects.filter(
        memberships__user=user, 
        is_archived=False
    ).exclude(owner=user)
    return owned.union(member_of)


def can_edit_board(user, board):
    """Verifica se usuário pode editar o quadro - simplificado para permitir todos os usuários autenticados"""
    return True  # Todos os usuários autenticados podem editar


def can_view_board(user, board):
    """Verifica se usuário pode visualizar o quadro - simplificado para permitir todos"""
    return True  # Todos os usuários autenticados podem visualizar


def board_to_dict(board, include_lists=False):
    """Converte quadro para dicionário"""
    data = {
        'id': board.id,
        'name': board.name,
        'description': board.description,
        'background_color': board.background_color,
        'background_image': board.background_image,
        'visibility': board.visibility,
        'is_favorite': board.is_favorite,
        'owner': {
            'id': board.owner.id,
            'name': board.owner.get_full_name() or board.owner.username,
        },
        'created_at': board.created_at.isoformat(),
    }
    if include_lists:
        data['lists'] = [list_to_dict(lst, include_cards=True) for lst in board.lists.filter(is_archived=False)]
        data['labels'] = [{'id': l.id, 'name': l.name, 'color': l.color} for l in board.labels.all()]
        data['members'] = [
            {
                'id': m.user.id,
                'name': m.user.get_full_name() or m.user.username,
                'role': m.role,
                'initials': get_user_initials(m.user)
            }
            for m in board.memberships.all()
        ]
    return data


def list_to_dict(lst, include_cards=False):
    """Converte lista para dicionário"""
    data = {
        'id': lst.id,
        'name': lst.name,
        'position': lst.position,
        'card_limit': lst.card_limit,
        'card_count': lst.cards.filter(is_archived=False).count(),
    }
    if include_cards:
        data['cards'] = [card_to_dict(card) for card in lst.cards.filter(is_archived=False)]
    return data


def card_to_dict(card):
    """Converte cartão para dicionário"""
    progress = card.checklist_progress
    return {
        'id': card.id,
        'title': card.title,
        'description': card.description[:100] + '...' if len(card.description) > 100 else card.description,
        'position': card.position,
        'cover_color': card.cover_color,
        'cover_image': card.cover_image,
        'due_date': card.due_date.isoformat() if card.due_date else None,
        'due_complete': card.due_complete,
        'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in card.labels.all()],
        'assigned_to': [
            {'id': u.id, 'name': u.get_full_name() or u.username, 'initials': get_user_initials(u)}
            for u in card.assigned_to.all()
        ],
        'has_description': bool(card.description),
        'comment_count': card.comments.count(),
        'attachment_count': card.attachments.count(),
        'checklist_progress': progress,
    }


def card_to_detail_dict(card):
    """Converte cartão para dicionário detalhado (modal)"""
    data = card_to_dict(card)
    data['description'] = card.description
    data['list'] = {'id': card.list.id, 'name': card.list.name}
    data['board'] = {'id': card.list.board.id, 'name': card.list.board.name}
    data['checklists'] = [
        {
            'id': cl.id,
            'title': cl.title,
            'items': [
                {
                    'id': item.id,
                    'text': item.text,
                    'is_completed': item.is_completed,
                }
                for item in cl.items.all()
            ]
        }
        for cl in card.checklists.all()
    ]
    data['comments'] = [
        {
            'id': c.id,
            'author': {
                'id': c.author.id,
                'name': c.author.get_full_name() or c.author.username,
                'initials': get_user_initials(c.author)
            },
            'content': c.content,
            'created_at': c.created_at.isoformat(),
        }
        for c in card.comments.all()[:20]
    ]
    data['activities'] = [
        {
            'id': a.id,
            'user': a.user.get_full_name() or a.user.username,
            'user_initials': get_user_initials(a.user),
            'action': a.get_action_display(),
            'description': a.description,
            'created_at': a.created_at.isoformat(),
        }
        for a in card.activities.all()[:20]
    ]
    data['created_by'] = {
        'id': card.created_by.id,
        'name': card.created_by.get_full_name() or card.created_by.username,
    }
    data['created_at'] = card.created_at.isoformat()
    return data


def get_user_initials(user):
    name = user.get_full_name() or user.username
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def log_activity(card, user, action, description):
    """Registra atividade no cartão"""
    user_name = user.get_full_name() or user.username
    full_description = f"<strong>{user_name}</strong> {description}"
    CardActivity.objects.create(
        card=card,
        user=user,
        action=action,
        description=full_description
    )


# ============================================
# BOARDS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def api_boards(request):
    """Lista quadros ou cria novo"""
    if request.method == "GET":
        boards = get_user_boards(request.user)
        return JsonResponse({
            'boards': [board_to_dict(b) for b in boards]
        })
    
    # POST - Criar quadro
    try:
        data = json.loads(request.body)
        board = KanbanBoard.objects.create(
            name=data.get('name', 'Novo Quadro'),
            description=data.get('description', ''),
            background_color=data.get('background_color', '#0079bf'),
            visibility=data.get('visibility', 'private'),
            owner=request.user
        )
        # Cria labels padrão
        default_colors = ['#61bd4f', '#f2d600', '#ff9f1a', '#eb5a46', '#c377e0', '#0079bf']
        for color in default_colors:
            CardLabel.objects.create(board=board, color=color)
        
        return JsonResponse(board_to_dict(board, include_lists=True))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_board_detail(request, board_id):
    """Detalhe, atualização ou exclusão de quadro"""
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if not can_view_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "GET":
        return JsonResponse(board_to_dict(board, include_lists=True))
    
    if not can_edit_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão de edição'}, status=403)
    
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            if 'name' in data:
                board.name = data['name']
            if 'description' in data:
                board.description = data['description']
            if 'background_color' in data:
                board.background_color = data['background_color']
            if 'background_image' in data:
                board.background_image = data['background_image']
            if 'visibility' in data:
                board.visibility = data['visibility']
            if 'is_favorite' in data:
                board.is_favorite = data['is_favorite']
            board.save()
            return JsonResponse(board_to_dict(board))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "DELETE":
        if board.owner != request.user:
            return JsonResponse({'error': 'Apenas o dono pode excluir'}, status=403)
        board.is_archived = True
        board.save()
        return JsonResponse({'deleted': True})


# ============================================
# LISTS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def api_board_lists(request, board_id):
    """Lista ou cria listas em um quadro"""
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if not can_view_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "GET":
        lists = board.lists.filter(is_archived=False)
        return JsonResponse({
            'lists': [list_to_dict(lst, include_cards=True) for lst in lists]
        })
    
    if not can_edit_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão de edição'}, status=403)
    
    # POST - Criar lista
    try:
        data = json.loads(request.body)
        max_pos = board.lists.aggregate(Max('position'))['position__max'] or 0
        lst = KanbanList.objects.create(
            board=board,
            name=data.get('name', 'Nova Lista'),
            position=max_pos + 1
        )
        return JsonResponse(list_to_dict(lst, include_cards=True))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["PUT", "DELETE"])
def api_list_detail(request, list_id):
    """Atualiza ou exclui lista"""
    lst = get_object_or_404(KanbanList, id=list_id)
    
    if not can_edit_board(request.user, lst.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            if 'name' in data:
                lst.name = data['name']
            if 'position' in data:
                lst.position = data['position']
            if 'card_limit' in data:
                lst.card_limit = data['card_limit']
            lst.save()
            return JsonResponse(list_to_dict(lst))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "DELETE":
        lst.is_archived = True
        lst.save()
        return JsonResponse({'deleted': True})


@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_lists_reorder(request, board_id):
    """Reordena listas de um quadro"""
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if not can_edit_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        order = data.get('order', [])  # Lista de IDs na nova ordem
        for idx, list_id in enumerate(order):
            KanbanList.objects.filter(id=list_id, board=board).update(position=idx)
        return JsonResponse({'reordered': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# CARDS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def api_list_cards(request, list_id):
    """Lista ou cria cartões em uma lista"""
    lst = get_object_or_404(KanbanList, id=list_id)
    
    if not can_view_board(request.user, lst.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "GET":
        cards = lst.cards.filter(is_archived=False)
        return JsonResponse({
            'cards': [card_to_dict(c) for c in cards]
        })
    
    if not can_edit_board(request.user, lst.board):
        return JsonResponse({'error': 'Sem permissão de edição'}, status=403)
    
    # POST - Criar cartão
    try:
        data = json.loads(request.body)
        max_pos = lst.cards.aggregate(Max('position'))['position__max'] or 0
        card = KanbanCard.objects.create(
            list=lst,
            title=data.get('title', 'Novo Cartão'),
            description=data.get('description', ''),
            position=max_pos + 1,
            created_by=request.user
        )
        log_activity(card, request.user, 'created', f'criou este cartão na lista {lst.name}')
        return JsonResponse(card_to_dict(card))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_card_detail(request, card_id):
    """Detalhe, atualização ou exclusão de cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_view_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "GET":
        return JsonResponse(card_to_detail_dict(card))
    
    if not can_edit_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão de edição'}, status=403)
    
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            if 'title' in data:
                card.title = data['title']
            if 'description' in data:
                card.description = data['description']
                log_activity(card, request.user, 'updated', 'atualizou a descrição')
            if 'cover_color' in data:
                card.cover_color = data['cover_color']
            if 'due_date' in data:
                due_date_value = data['due_date']
                if due_date_value:
                    from datetime import datetime
                    # Handle both ISO format and datetime-local format
                    try:
                        card.due_date = datetime.fromisoformat(due_date_value.replace('Z', '+00:00'))
                    except ValueError:
                        card.due_date = datetime.strptime(due_date_value, '%Y-%m-%dT%H:%M')
                else:
                    card.due_date = None
                log_activity(card, request.user, 'due_date', 'alterou a data de entrega')
            if 'due_complete' in data:
                card.due_complete = data['due_complete']
            card.save()
            return JsonResponse(card_to_detail_dict(card))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "DELETE":
        # Log activity before deletion while card still exists
        log_activity(card, request.user, 'deleted', 'excluiu este cartão permanentemente')
        card.delete()
        return JsonResponse({'deleted': True})


@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_card_move(request, card_id):
    """Move cartão para outra lista"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_edit_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        new_list_id = data.get('list_id')
        new_position = data.get('position', 0)
        
        old_list = card.list
        new_list = get_object_or_404(KanbanList, id=new_list_id)
        
        # Verifica se é do mesmo quadro
        if new_list.board != old_list.board:
            return JsonResponse({'error': 'Listas devem ser do mesmo quadro'}, status=400)
        
        card.list = new_list
        card.position = new_position
        card.save()
        
        if old_list.id != new_list.id:
            log_activity(card, request.user, 'moved', f'moveu de {old_list.name} para {new_list.name}')
        
        return JsonResponse({'moved': True, 'card': card_to_dict(card)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_cards_reorder(request, list_id):
    """Reordena cartões de uma lista"""
    lst = get_object_or_404(KanbanList, id=list_id)
    
    if not can_edit_board(request.user, lst.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
        for idx, card_id in enumerate(order):
            KanbanCard.objects.filter(id=card_id, list=lst).update(position=idx)
        return JsonResponse({'reordered': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# LABELS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_card_labels(request, card_id):
    """Adiciona ou remove labels do cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_edit_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        label_id = data.get('label_id')
        action = data.get('action', 'add')  # 'add' ou 'remove'
        
        label = get_object_or_404(CardLabel, id=label_id, board=card.list.board)
        
        if action == 'add':
            card.labels.add(label)
            log_activity(card, request.user, 'label_added', f'adicionou a etiqueta {label.name or label.color}')
        else:
            card.labels.remove(label)
            log_activity(card, request.user, 'label_removed', f'removeu a etiqueta {label.name or label.color}')
        
        return JsonResponse({'success': True, 'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in card.labels.all()]})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# CHECKLISTS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_card_checklists(request, card_id):
    """Cria checklist no cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_edit_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        checklist = Checklist.objects.create(
            card=card,
            title=data.get('title', 'Checklist'),
            position=card.checklists.count()
        )
        log_activity(card, request.user, 'checklist_added', f'adicionou checklist "{checklist.title}"')
        return JsonResponse({
            'id': checklist.id,
            'title': checklist.title,
            'items': []
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["POST", "PUT", "DELETE"])
def api_checklist_items(request, checklist_id):
    """Gerencia itens do checklist"""
    checklist = get_object_or_404(Checklist, id=checklist_id)
    
    if not can_edit_board(request.user, checklist.card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "POST":
        # Criar item
        try:
            data = json.loads(request.body)
            item = ChecklistItem.objects.create(
                checklist=checklist,
                text=data.get('text', 'Novo item'),
                position=checklist.items.count()
            )
            return JsonResponse({
                'id': item.id,
                'text': item.text,
                'is_completed': item.is_completed
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "PUT":
        # Atualizar item
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            item = get_object_or_404(ChecklistItem, id=item_id, checklist=checklist)
            
            if 'text' in data:
                item.text = data['text']
            if 'is_completed' in data:
                item.is_completed = data['is_completed']
            item.save()
            
            return JsonResponse({
                'id': item.id,
                'text': item.text,
                'is_completed': item.is_completed
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            item = get_object_or_404(ChecklistItem, id=item_id, checklist=checklist)
            item.delete()
            return JsonResponse({'deleted': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


# ============================================
# COMMENTS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_card_comments(request, card_id):
    """Adiciona comentário ao cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_view_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        comment = CardComment.objects.create(
            card=card,
            author=request.user,
            content=data.get('content', '')
        )
        log_activity(card, request.user, 'commented', 'comentou neste cartão')
        
        return JsonResponse({
            'id': comment.id,
            'author': {
                'id': comment.author.id,
                'name': comment.author.get_full_name() or comment.author.username,
                'initials': get_user_initials(comment.author)
            },
            'content': comment.content,
            'created_at': comment.created_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# MEMBERS ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def api_card_members(request, card_id):
    """Adiciona ou remove membros do cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if not can_edit_board(request.user, card.list.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        action = data.get('action', 'add')
        
        member = get_object_or_404(User, id=user_id)
        
        if action == 'add':
            card.assigned_to.add(member)
            log_activity(card, request.user, 'assigned', f'atribuiu a {member.get_full_name() or member.username}')
        else:
            card.assigned_to.remove(member)
        
        return JsonResponse({
            'success': True,
            'assigned_to': [
                {'id': u.id, 'name': u.get_full_name() or u.username, 'initials': get_user_initials(u)}
                for u in card.assigned_to.all()
            ]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# SEARCH
# ============================================

@api_login_required
@require_http_methods(["GET"])
def api_kanban_search(request):
    """Busca cartões"""
    query = request.GET.get('q', '')
    board_id = request.GET.get('board_id')
    
    if not query:
        return JsonResponse({'cards': []})
    
    cards = KanbanCard.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        is_archived=False
    )
    
    if board_id:
        cards = cards.filter(list__board_id=board_id)
    
    # Filtra por quadros que o usuário tem acesso
    user_boards = get_user_boards(request.user).values_list('id', flat=True)
    cards = cards.filter(list__board_id__in=user_boards)[:20]
    
    return JsonResponse({
        'cards': [
            {
                'id': c.id,
                'title': c.title,
                'list_name': c.list.name,
                'board_name': c.list.board.name,
                'board_id': c.list.board.id
            }
            for c in cards
        ]
    })


# ============================================
# MEMBERS
# ============================================

@api_login_required
@require_http_methods(["POST"])
def api_card_members(request, card_id):
    """Gerencia membros atribuídos ao cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        action = data.get('action', 'add')  # 'add' ou 'remove'
        
        if not member_id:
            return JsonResponse({'error': 'member_id é obrigatório'}, status=400)
        
        member = get_object_or_404(User, id=member_id)
        
        if action == 'add':
            card.assigned_to.add(member)
            CardActivity.objects.create(
                card=card,
                user=request.user,
                action='assigned',
                description=f'{request.user.get_full_name() or request.user.username} atribuiu {member.get_full_name() or member.username} ao cartão'
            )
        else:
            card.assigned_to.remove(member)
            CardActivity.objects.create(
                card=card,
                user=request.user,
                action='assigned',
                description=f'{request.user.get_full_name() or request.user.username} removeu {member.get_full_name() or member.username} do cartão'
            )
        
        return JsonResponse({
            'success': True,
            'assigned_to': [
                {'id': u.id, 'name': u.get_full_name() or u.username, 'initials': get_user_initials(u)}
                for u in card.assigned_to.all()
            ]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# ATTACHMENTS
# ============================================

@api_login_required
@require_http_methods(["GET", "POST"])
def api_card_attachments(request, card_id):
    """Gerencia anexos do cartão"""
    card = get_object_or_404(KanbanCard, id=card_id)
    
    if request.method == 'GET':
        attachments = card.attachments.all()
        return JsonResponse([
            {
                'id': att.id,
                'filename': att.filename,
                'url': att.file.url,
                'uploaded_at': att.uploaded_at.strftime('%d/%m/%Y %H:%M'),
                'uploaded_by': att.uploaded_by.get_full_name() or att.uploaded_by.username
            }
            for att in attachments
        ], safe=False)
    
    elif request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'Arquivo não encontrado'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        attachment = CardAttachment.objects.create(
            card=card,
            file=uploaded_file,
            filename=uploaded_file.name,
            uploaded_by=request.user
        )
        
        CardActivity.objects.create(
            card=card,
            user=request.user,
            action='attachment_added',
            description=f'{request.user.get_full_name() or request.user.username} adicionou o anexo "{uploaded_file.name}"'
        )
        
        return JsonResponse({
            'id': attachment.id,
            'filename': attachment.filename,
            'url': attachment.file.url,
            'uploaded_at': attachment.uploaded_at.strftime('%d/%m/%Y %H:%M')
        }, status=201)


@api_login_required
@require_http_methods(["DELETE"])
def api_card_attachment_delete(request, card_id, attachment_id):
    """Exclui um anexo específico"""
    card = get_object_or_404(KanbanCard, id=card_id)
    attachment = get_object_or_404(CardAttachment, id=attachment_id, card=card)
    
    filename = attachment.filename
    attachment.file.delete(save=False)  # Delete the file
    attachment.delete()
    
    CardActivity.objects.create(
        card=card,
        user=request.user,
        action='attachment_added',
        description=f'{request.user.get_full_name() or request.user.username} removeu o anexo "{filename}"'
    )
    
    return JsonResponse({'success': True})



# ============================================
# LABELS CRUD ENDPOINTS
# ============================================

@csrf_exempt
@api_login_required
@require_http_methods(["GET", "POST"])
def api_board_labels(request, board_id):
    """Lista ou cria labels do quadro"""
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if not can_view_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "GET":
        labels = board.labels.all()
        return JsonResponse({
            'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in labels]
        })
    
    # POST - Criar label
    if not can_edit_board(request.user, board):
        return JsonResponse({'error': 'Sem permissão de edição'}, status=403)
    
    try:
        data = json.loads(request.body)
        label = CardLabel.objects.create(
            board=board,
            name=data.get('name', ''),
            color=data.get('color', '#61bd4f')
        )
        return JsonResponse({
            'id': label.id,
            'name': label.name,
            'color': label.color
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["PUT", "DELETE"])
def api_label_detail(request, label_id):
    """Atualiza ou exclui label"""
    label = get_object_or_404(CardLabel, id=label_id)
    
    if not can_edit_board(request.user, label.board):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            if 'name' in data:
                label.name = data['name']
            if 'color' in data:
                label.color = data['color']
            label.save()
            return JsonResponse({
                'id': label.id,
                'name': label.name,
                'color': label.color
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    if request.method == "DELETE":
        label.delete()
        return JsonResponse({'deleted': True})
