from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import json

from ..models import RefundRequest, RefundRequestAttachment, User, Department


@login_required
@require_http_methods(["POST"])
def api_refund_create(request):
    """Criar nova solicitação de estorno (NRS Suporte)"""
    try:
        # Support both FormData and JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData submission (with potential file uploads)
            data = request.POST
            checked_cameras = data.get('checked_cameras', 'false').lower() == 'true'
            refund_value_str = data.get('refund_value', '0').replace('.', '').replace(',', '.')
            try:
                refund_value = float(refund_value_str)
            except:
                refund_value = 0
        else:
            # JSON submission (legacy)
            data = json.loads(request.body)
            checked_cameras = data.get('checked_cameras', False)
            refund_value = data.get('refund_value', 0)
        
        refund = RefundRequest.objects.create(
            analyst=request.user,
            store_code=data.get('store_code', ''),
            customer_name=data.get('customer_name', ''),
            customer_cpf=data.get('customer_cpf', ''),
            customer_email=data.get('customer_email', ''),
            customer_phone=data.get('customer_phone', ''),
            incident_date=data.get('incident_date'),
            incident_time=data.get('incident_time') or None,
            purchase_location=data.get('purchase_location', 'loja_fisica'),
            reason=data.get('reason', ''),
            checked_cameras=checked_cameras,
            refund_value=refund_value,
            refund_type=data.get('refund_type', 'pix'),
            pix_key=data.get('pix_key', ''),
            summary=data.get('summary', ''),
        )
        
        # Process file attachments if present
        files = request.FILES.getlist('attachments')
        for file in files[:5]:  # Limit to 5 files
            RefundRequestAttachment.objects.create(
                refund_request=refund,
                file=file,
                uploaded_by=request.user,
                description=f'Anexo enviado na criação'
            )
        
        return JsonResponse({
            'success': True,
            'id': refund.id,
            'message': f'Solicitação #{refund.id} criada com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_refund_list(request):
    """Listar solicitações de estorno com filtros de busca"""
    user = request.user
    
    # Check if requesting all NRS Suporte requests
    show_all = request.GET.get('all', '').lower() == 'true'
    
    # If show_all and user is from NRS Suporte, show all NRS requests
    if show_all and user.department and user.department.name == 'NRS Suporte':
        refunds = RefundRequest.objects.all()
    elif user.department and user.department.name == 'CS Clientes':
        refunds = RefundRequest.objects.all()
    elif user.role in ['gestor', 'administrador']:
        refunds = RefundRequest.objects.all()
    else:
        refunds = RefundRequest.objects.filter(analyst=user)
    
    # Filtrar por status
    status_filter = request.GET.get('status')
    if status_filter:
        refunds = refunds.filter(status=status_filter)
    
    # Filtrar por analista
    analyst_filter = request.GET.get('analyst')
    if analyst_filter:
        refunds = refunds.filter(analyst_id=analyst_filter)
    
    # Filtrar por loja
    store_filter = request.GET.get('store', '').strip()
    if store_filter:
        refunds = refunds.filter(store_code__icontains=store_filter)
    
    # Filtrar por período
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    if date_start:
        refunds = refunds.filter(created_at__date__gte=date_start)
    if date_end:
        refunds = refunds.filter(created_at__date__lte=date_end)
    
    # Busca geral (nome, CPF, ID, email, responsável)
    search = request.GET.get('search', '').strip()
    if search:
        refunds = refunds.filter(
            Q(id__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_cpf__icontains=search) |
            Q(customer_email__icontains=search) |
            Q(store_code__icontains=search) |
            Q(analyst__first_name__icontains=search) |
            Q(analyst__last_name__icontains=search)
        )
    
    # Order by most recent
    refunds = refunds.order_by('-created_at')
    
    data = []
    for r in refunds:
        data.append({
            'id': str(r.id),
            'analyst_name': r.analyst.get_full_name() or r.analyst.username,
            'analyst_id': str(r.analyst.id),
            'store_code': r.store_code,
            'customer_name': r.customer_name,
            'customer_cpf': r.customer_cpf,
            'customer_email': r.customer_email,
            'refund_value': str(r.refund_value),
            'refund_type': r.get_refund_type_display(),
            'status': r.status,
            'status_display': r.get_status_display(),
            'created_at': r.created_at.isoformat(),
            'updated_at': r.updated_at.isoformat(),
            'viewed_by': r.viewed_by.get_full_name() if r.viewed_by else None,
            'viewed_at': r.viewed_at.isoformat() if r.viewed_at else None,
            'cancellation_requested': r.cancellation_requested,
        })
    
    return JsonResponse({'refunds': data})


@login_required
@require_http_methods(["GET"])
def api_refund_detail(request, pk):
    """Detalhes de uma solicitação de estorno"""
    try:
        refund = RefundRequest.objects.get(pk=pk)
        user = request.user
        
        # Se usuário é do CS Clientes e ainda não visualizou, marcar como visualizado
        if user.department and user.department.name == 'CS Clientes':
            if not refund.viewed_by:
                refund.viewed_by = user
                refund.viewed_at = timezone.now()
                refund.save(update_fields=['viewed_by', 'viewed_at'])
        
        attachments = []
        for att in refund.attachments.all():
            attachments.append({
                'id': att.id,
                'file_url': att.file.url if att.file else '',
                'description': att.description,
                'uploaded_by': att.uploaded_by.get_full_name() if att.uploaded_by else 'N/A',
                'uploaded_at': att.uploaded_at.isoformat(),
            })
        
        # Verificar permissões de edição
        is_nrs_suporte = user.department and user.department.name == 'NRS Suporte'
        can_edit = (
            user == refund.analyst or 
            user.role in ['gestor', 'administrador'] or
            is_nrs_suporte  # NRS Suporte pode editar todas as solicitações
        )
        
        # Verificar permissão de exclusão (gestores CS ou admin)
        can_delete = (
            user.role == 'administrador' or
            (user.role == 'gestor' and user.department and user.department.name == 'CS Clientes')
        )
        
        # Verificar permissão de cancelamento (gestores NRS)
        can_cancel = (
            user.role in ['gestor', 'administrador'] and
            user.department and user.department.name == 'NRS Suporte'
        )
        
        data = {
            'id': str(refund.id),
            'analyst_name': refund.analyst.get_full_name() or refund.analyst.username,
            'analyst_id': str(refund.analyst.id),
            'store_code': refund.store_code,
            'customer_name': refund.customer_name,
            'customer_cpf': refund.customer_cpf,
            'customer_email': refund.customer_email,
            'customer_phone': refund.customer_phone,
            'incident_date': refund.incident_date.isoformat(),
            'incident_time': refund.incident_time.isoformat() if refund.incident_time else None,
            'purchase_location': refund.get_purchase_location_display(),
            'reason': refund.reason,
            'checked_cameras': refund.checked_cameras,
            'refund_value': str(refund.refund_value),
            'refund_type': refund.get_refund_type_display(),
            'refund_type_raw': refund.refund_type,
            'pix_key': refund.pix_key,
            'summary': refund.summary,
            'status': refund.status,
            'status_display': refund.get_status_display(),
            'created_at': refund.created_at.isoformat(),
            'updated_at': refund.updated_at.isoformat(),
            'completed_at': refund.completed_at.isoformat() if refund.completed_at else None,
            'viewed_by': refund.viewed_by.get_full_name() if refund.viewed_by else None,
            'viewed_at': refund.viewed_at.isoformat() if refund.viewed_at else None,
            'cancellation_requested': refund.cancellation_requested,
            'cancellation_requested_by': refund.cancellation_requested_by.get_full_name() if refund.cancellation_requested_by else None,
            'cancellation_requested_at': refund.cancellation_requested_at.isoformat() if refund.cancellation_requested_at else None,
            'cancellation_reason': refund.cancellation_reason,
            'attachments': attachments,
            'can_edit': can_edit,
            'can_delete': can_delete,
            'can_cancel': can_cancel,
        }

        
        return JsonResponse({'success': True, 'refund': data})
    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)


@login_required
@require_http_methods(["PATCH", "POST"])
def api_refund_update_status(request, pk):
    """Atualizar status da solicitação (CS Clientes)"""
    try:
        refund = RefundRequest.objects.get(pk=pk)
        data = json.loads(request.body)
        
        new_status = data.get('status')
        if new_status and new_status in ['aberta', 'em_analise', 'concluida', 'cancelada']:
            refund.status = new_status
            
            if new_status == 'concluida':
                refund.completed_at = timezone.now()
                refund.notified_nrs_completion = False
            
            refund.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Status atualizado para {refund.get_status_display()}'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Status inválido'}, status=400)
    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_refund_request_cancellation(request, pk):
    """Solicitar cancelamento de uma solicitação (apenas gestores NRS)"""
    try:
        user = request.user
        
        # Verificar permissão
        if user.role not in ['gestor', 'administrador']:
            return JsonResponse({'success': False, 'error': 'Sem permissão para solicitar cancelamento'}, status=403)
        
        refund = RefundRequest.objects.get(pk=pk)
        data = json.loads(request.body)
        
        refund.cancellation_requested = True
        refund.cancellation_requested_by = user
        refund.cancellation_requested_at = timezone.now()
        refund.cancellation_reason = data.get('reason', '')
        refund.save(update_fields=['cancellation_requested', 'cancellation_requested_by', 'cancellation_requested_at', 'cancellation_reason'])
        
        return JsonResponse({
            'success': True,
            'message': f'Cancelamento solicitado para #{refund.id}'
        })

    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)


@login_required
@require_http_methods(["DELETE", "POST"])
def api_refund_delete(request, pk):
    """Excluir uma solicitação (apenas gestores CS Clientes ou admin)"""
    try:
        user = request.user
        
        # Verificar permissão
        is_admin = user.role == 'administrador'
        is_cs_gestor = user.role == 'gestor' and user.department and user.department.name == 'CS Clientes'
        
        if not (is_admin or is_cs_gestor):
            return JsonResponse({'success': False, 'error': 'Sem permissão para excluir'}, status=403)
        
        refund = RefundRequest.objects.get(pk=pk)
        refund_id = refund.id
        refund.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Solicitação #{refund_id} excluída com sucesso'
        })
    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)


@login_required
@require_http_methods(["POST"])
def api_refund_add_attachment(request, pk):
    """Adicionar anexo a uma solicitação"""
    try:
        refund = RefundRequest.objects.get(pk=pk)
        
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo enviado'}, status=400)
        
        file = request.FILES['file']
        description = request.POST.get('description', '')
        
        attachment = RefundRequestAttachment.objects.create(
            refund_request=refund,
            file=file,
            uploaded_by=request.user,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'attachment_id': attachment.id,
            'file_url': attachment.file.url,
            'message': 'Anexo adicionado com sucesso!'
        })
    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)


@login_required
@require_http_methods(["GET"])
def api_refund_notifications(request):
    """Verificar notificações de solicitações de estorno"""
    user = request.user
    notifications = []
    
    # Para CS Clientes: novas solicitações não notificadas
    if user.department and user.department.name == 'CS Clientes':
        new_refunds = RefundRequest.objects.filter(notified_cs=False)
        for r in new_refunds:
            notifications.append({
                'type': 'new_refund',
                'message': f'Nova solicitação #{r.id} de {r.analyst.get_full_name() or r.analyst.username}: {r.customer_name} - R$ {r.refund_value}'
            })
            r.notified_cs = True
            r.save(update_fields=['notified_cs'])
    
    # Para NRS Suporte: solicitações concluídas
    else:
        completed_refunds = RefundRequest.objects.filter(
            analyst=user,
            status='concluida',
            notified_nrs_completion=False
        )
        for r in completed_refunds:
            notifications.append({
                'type': 'refund_completed',
                'message': f'Sua solicitação #{r.id} para {r.customer_name} foi concluída!'
            })
            r.notified_nrs_completion = True
            r.save(update_fields=['notified_nrs_completion'])
    
    return JsonResponse({
        'has_notifications': len(notifications) > 0,
        'notifications': notifications
    })


@login_required
@require_http_methods(["GET"])
def api_refund_stats(request):
    """Estatísticas de solicitações para dashboard CS Clientes"""
    total = RefundRequest.objects.count()
    resolved = RefundRequest.objects.filter(status='concluida').count()
    pending = RefundRequest.objects.filter(status='aberta').count()
    in_analysis = RefundRequest.objects.filter(status='em_analise').count()
    cancelled = RefundRequest.objects.filter(status='cancelada').count()
    
    # Últimas 5 novas solicitações
    recent = RefundRequest.objects.filter(status='aberta').order_by('-created_at')[:5]
    recent_list = []
    for r in recent:
        recent_list.append({
            'id': r.id,
            'analyst_name': r.analyst.get_full_name() or r.analyst.username,
            'customer_name': r.customer_name,
            'refund_value': str(r.refund_value),
            'created_at': r.created_at.isoformat(),
        })
    
    return JsonResponse({
        'total': total,
        'resolved': resolved,
        'pending': pending,
        'in_analysis': in_analysis,
        'cancelled': cancelled,
        'recent': recent_list
    })


@login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def api_refund_edit(request, pk):
    """Editar uma solicitação de estorno existente"""
    try:
        refund = RefundRequest.objects.get(pk=pk)
        user = request.user
        
        # Verificar permissão de edição
        is_nrs_suporte = user.department and user.department.name == 'NRS Suporte'
        can_edit = (
            user == refund.analyst or 
            user.role in ['gestor', 'administrador'] or
            is_nrs_suporte  # NRS Suporte pode editar todas as solicitações
        )
        
        if not can_edit:
            return JsonResponse({'success': False, 'error': 'Sem permissão para editar'}, status=403)
        
        # Parse data
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.POST
            checked_cameras = data.get('checked_cameras', 'false').lower() == 'true'
            refund_value_str = data.get('refund_value', '0').replace('.', '').replace(',', '.')
            try:
                refund_value = float(refund_value_str)
            except:
                refund_value = float(refund.refund_value)
        else:
            data = json.loads(request.body)
            checked_cameras = data.get('checked_cameras', refund.checked_cameras)
            refund_value = data.get('refund_value', refund.refund_value)
        
        # Update fields
        refund.store_code = data.get('store_code', refund.store_code)
        refund.customer_name = data.get('customer_name', refund.customer_name)
        refund.customer_cpf = data.get('customer_cpf', refund.customer_cpf)
        refund.customer_email = data.get('customer_email', refund.customer_email)
        refund.customer_phone = data.get('customer_phone', refund.customer_phone)
        
        incident_date = data.get('incident_date')
        if incident_date:
            refund.incident_date = incident_date
        
        incident_time = data.get('incident_time')
        if incident_time:
            refund.incident_time = incident_time
            
        refund.purchase_location = data.get('purchase_location', refund.purchase_location)
        refund.reason = data.get('reason', refund.reason)
        refund.checked_cameras = checked_cameras
        refund.refund_value = refund_value
        refund.refund_type = data.get('refund_type', refund.refund_type)
        refund.pix_key = data.get('pix_key', refund.pix_key)
        refund.summary = data.get('summary', refund.summary)
        
        refund.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Solicitação #{refund.id} atualizada com sucesso!'
        })
    except RefundRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_nrs_analysts(request):
    """Retorna lista de analistas do NRS Suporte para filtros"""
    try:
        nrs_dept = Department.objects.filter(name='NRS Suporte').first()
        if not nrs_dept:
            return JsonResponse({'analysts': []})
        
        analysts = User.objects.filter(department=nrs_dept, is_active=True).order_by('first_name', 'last_name')
        
        data = []
        for u in analysts:
            data.append({
                'id': str(u.id),
                'name': u.get_full_name() or u.username
            })
        
        return JsonResponse({'analysts': data})
    except Exception as e:
        return JsonResponse({'analysts': [], 'error': str(e)})

