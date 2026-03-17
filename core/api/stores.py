"""
API endpoints for store verification presence tracking
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from ..models import Store, StoreViewerSession, StoreAudit
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_store_presence_heartbeat(request, store_id):
    """Register or update heartbeat for user viewing a store"""
    logger.info(f"[HEARTBEAT_START] Processing heartbeat for store {store_id} by user {request.user.username}")
    try:
        store = Store.objects.get(id=store_id)
        
        # Parse JSON body for is_auditing flag
        is_auditing = False
        if request.body:
            try:
                data = json.loads(request.body)
                is_auditing = data.get('is_auditing', False)
            except Exception as e:
                logger.warning(f"[HEARTBEAT_WARN] Failed to parse JSON body: {e}")
                pass
        
        # Create or update session
        session, created = StoreViewerSession.objects.update_or_create(
            store=store,
            user=request.user,
            defaults={'is_auditing': is_auditing}
        )
        
        # Get other active viewers
        other_viewers = StoreViewerSession.get_active_viewers(store, exclude_user=request.user)
        viewers_list = [{
            'id': v.user.id,
            'name': v.user.get_full_name() or v.user.username,
            'is_auditing': v.is_auditing
        } for v in other_viewers]
        
        return JsonResponse({
            'success': True,
            'viewers': viewers_list
        })
    except Store.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Loja não encontrada'}, status=404)
    except Exception as e:
        logger.error(f"[HEARTBEAT_ERROR] Unexpected error for store {store_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_store_presence_list(request, store_id):
    """Get list of users currently viewing a store"""
    try:
        store = Store.objects.get(id=store_id)
        
        viewers = StoreViewerSession.get_active_viewers(store, exclude_user=request.user)
        viewers_list = [{
            'id': v.user.id,
            'name': v.user.get_full_name() or v.user.username,
            'is_auditing': v.is_auditing
        } for v in viewers]
        
        return JsonResponse({
            'success': True,
            'viewers': viewers_list
        })
    except Store.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Loja não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_store_presence_leave(request, store_id):
    """Remove user from store viewing session"""
    try:
        StoreViewerSession.objects.filter(store_id=store_id, user=request.user).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_stores_all_presence(request):
    """Get presence info for all stores (for list view badges)"""
    try:
        # Get all active sessions (within last 15 seconds)
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(seconds=15)
        
        sessions = StoreViewerSession.objects.filter(
            last_heartbeat__gte=cutoff
        ).exclude(user=request.user).select_related('store', 'user')
        
        # Group by store
        presence_data = {}
        for session in sessions:
            store_id = session.store_id
            if store_id not in presence_data:
                presence_data[store_id] = []
            presence_data[store_id].append({
                'id': session.user.id,
                'name': session.user.get_full_name() or session.user.username,
                'is_auditing': session.is_auditing
            })
        
        return JsonResponse({
            'success': True,
            'presence': presence_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_store_audit_history(request, store_id):
    """Get full audit history for a store"""
    try:
        store = Store.objects.get(id=store_id)
        
        audits = StoreAudit.objects.filter(store=store).select_related('analyst').prefetch_related('items').order_by('-created_at')
        
        history = []
        for audit in audits:
            items_data = []
            for item in audit.items.all():
                resolution_info = None
                if item.issue and item.issue.status == 'resolvida':
                    resolution_info = {
                'resolved_by': item.issue.resolved_by.get_full_name() or item.issue.resolved_by.username if item.issue.resolved_by else 'Desconhecido',
                        'resolved_at': timezone.localtime(item.issue.resolved_at).strftime('%d/%m/%Y %H:%M') if item.issue.resolved_at else '',
                        'notes': item.issue.gestor_notes,
                    }

                items_data.append({
                    'name': item.get_item_name_display(),
                    'is_compliant': item.is_compliant,
                    'description': item.description,
                    'resolution': resolution_info
                })
            
            history.append({
                'id': audit.id,
                'date': timezone.localtime(audit.created_at).strftime('%d/%m/%Y %H:%M'),
                'analyst': audit.analyst.get_full_name() or audit.analyst.username,
                'has_irregularities': audit.has_irregularities(),
                'items': items_data
            })
        
        return JsonResponse({
            'success': True,
            'store_code': store.code,
            'history': history
        })
    except Store.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Loja não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
