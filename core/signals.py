from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Complaint, Colaborador, Empresa, Department, Turno

@receiver([post_save, post_delete], sender=Complaint)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """Limpa o cache do dashboard quando uma reclamação é criada, alterada ou deletada."""
    # Limpa cache do departamento específico se houver
    if instance.department_id:
        cache.delete(f'dashboard:stats:dept_{instance.department_id}')
    
    # Limpa cache global (para admins que veem tudo)
    cache.delete('dashboard:stats:global')
    print(f"✓ Cache do Dashboard invalidado (Complaint {instance.id})")

@receiver([post_save, post_delete], sender=Colaborador)
@receiver([post_save, post_delete], sender=Empresa)
@receiver([post_save, post_delete], sender=Department)
@receiver([post_save, post_delete], sender=Turno)
def invalidate_auxiliary_data_cache(sender, **kwargs):
    """Limpa o cache de dados auxiliares quando entidades relacionadas mudam."""
    cache.delete('aux_data:all')
    print(f"✓ Cache de Dados Auxiliares invalidado ({sender.__name__})")
