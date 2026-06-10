from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Colaborador, Empresa, Department, Turno

@receiver([post_save, post_delete], sender=Colaborador)
@receiver([post_save, post_delete], sender=Empresa)
@receiver([post_save, post_delete], sender=Department)
@receiver([post_save, post_delete], sender=Turno)
def invalidate_auxiliary_data_cache(sender, **kwargs):
    """Limpa o cache de dados auxiliares quando entidades relacionadas mudam."""
    cache.delete('aux_data:all')
    print(f"✓ Cache de Dados Auxiliares invalidado ({sender.__name__})")

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from .models import AuditLog

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    tenant = getattr(user, 'department', None)
    AuditLog.objects.create(
        usuario=user,
        action='login',
        tenant=tenant,
        ip_address=ip,
        detalhes_json={'event': 'login_success'}
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        ip = get_client_ip(request)
        tenant = getattr(user, 'department', None)
        AuditLog.objects.create(
            usuario=user,
            action='logout',
            tenant=tenant,
            ip_address=ip,
            detalhes_json={'event': 'logout'}
        )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    username = credentials.get('username') if credentials else 'Unknown'
    AuditLog.objects.create(
        action='login',
        ip_address=ip,
        detalhes_json={'event': 'login_failed', 'username': username}
    )
