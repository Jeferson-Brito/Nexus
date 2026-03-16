from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import json
from .models import ChatInactivityRequest, User

@login_required
def api_chat_inactivity_list(request):
    """Lista as solicitações de inatividade"""
    user = request.user
    is_manager = user.role in ['gestor', 'administrador']
    
    queryset = ChatInactivityRequest.objects.all().select_related('analyst', 'reviewed_by').order_by('created_at')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
        
    analyst_id = request.GET.get('analyst_id')
    if analyst_id:
        queryset = queryset.filter(analyst_id=analyst_id)
    elif not is_manager:
        # Se não for gestor, vê apenas as suas
        queryset = queryset.filter(analyst=user)
        
    search = request.GET.get('q')
    if search:
        queryset = queryset.filter(
            Q(chat_id__icontains=search) |
            Q(chat_link__icontains=search) |
            Q(analyst__first_name__icontains=search) |
            Q(analyst__last_name__icontains=search)
        )

    chat_date = request.GET.get('chat_date')
    if chat_date:
        queryset = queryset.filter(chat_date=chat_date)

    date_start = request.GET.get('date_start')
    if date_start:
        queryset = queryset.filter(created_at__date__gte=date_start)

    date_end = request.GET.get('date_end')
    if date_end:
        queryset = queryset.filter(created_at__date__lte=date_end)
        
    requests_data = []
    for r in queryset:
        requests_data.append({
            'id': str(r.id),
            'chat_id': r.chat_id,
            'chat_link': r.chat_link,
            'chat_date': r.chat_date.strftime('%d/%m/%Y'),
            'was_inactivity': r.was_inactivity,
            'analyst_name': r.analyst.get_full_name() or r.analyst.username,
            'status': r.status,
            'created_at': timezone.localtime(r.created_at).strftime('%d/%m/%Y %H:%M'),
            'reviewed_by_name': r.reviewed_by.get_full_name() or r.reviewed_by.username if r.reviewed_by else None,
            'reviewed_at': timezone.localtime(r.reviewed_at).strftime('%d/%m/%Y %H:%M') if r.reviewed_at else None,
            'analyst_id': str(r.analyst.id),
            'review_notes': r.review_notes
        })
        
    return JsonResponse(requests_data, safe=False)

@login_required
def api_chat_inactivity_create(request):
    """Cria uma ou mais solicitações de inatividade"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
        
    try:
        data = json.loads(request.body)
        chat_ids = data.get('chat_ids', []) # Lista de IDs
        chat_links = data.get('chat_links', []) # Lista de Links (correspondentes aos IDs)
        chat_date = data.get('chat_date')
        was_inactivity = data.get('was_inactivity', True)
        
        if not chat_ids or not chat_date:
            return JsonResponse({'error': 'IDs e Data são obrigatórios'}, status=400)
            
        created_count = 0
        # Garante que temos o mesmo número de links que de IDs ou usa link vazio
        for i, cid in enumerate(chat_ids):
            link = chat_links[i] if i < len(chat_links) else ""
            
            ChatInactivityRequest.objects.create(
                analyst=request.user,
                chat_id=cid.strip(),
                chat_link=link.strip(),
                chat_date=chat_date,
                was_inactivity=was_inactivity
            )
            created_count += 1
            
        return JsonResponse({
            'success': True, 
            'message': f'{created_count} solicitações criadas com sucesso.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_chat_inactivity_action(request, pk):
    """Aprova ou reprova uma solicitação (Apenas Gestor/Admin)"""
    if request.user.role not in ['gestor', 'administrador']:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
        
    req = get_object_or_404(ChatInactivityRequest, pk=pk)
    
    try:
        data = json.loads(request.body)
        action = data.get('action') # 'aprovado' ou 'reprovado'
        notes = data.get('notes', '')
        
        if action not in ['aprovado', 'reprovado']:
            return JsonResponse({'error': 'Ação inválida'}, status=400)
            
        req.status = action
        req.review_notes = notes
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save()
        
        return JsonResponse({'success': True, 'message': f'Solicitação {action} com sucesso.'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_chat_inactivity_delete(request, pk):
    """Exclui uma solicitação (Analista pode excluir enquanto pendente, Gestor pode sempre)"""
    req = get_object_or_404(ChatInactivityRequest, pk=pk)
    user = request.user
    
    is_manager = user.role in ['gestor', 'administrador']
    is_owner = req.analyst == user
    
    if not is_manager and not (is_owner and req.status == 'pendente'):
        return JsonResponse({'error': 'Você não tem permissão para excluir esta solicitação.'}, status=403)
        
    req.delete()
    return JsonResponse({'success': True, 'message': 'Solicitação excluída.'})
