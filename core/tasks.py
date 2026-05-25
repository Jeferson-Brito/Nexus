from celery import shared_task
from django.utils import timezone
from .models import Complaint, IAQuota, IAConsumptionLog

@shared_task(bind=True, max_retries=3)
def task_classificar_reclamacao(self, complaint_id, descricao, tipo_reclamacao, user_id=None, tenant_id=None):
    from .services.ia_service import classificar_reclamacao
    try:
        # Check Quota
        if tenant_id:
            quota, created = IAQuota.objects.get_or_create(tenant_id=tenant_id)
            hoje = timezone.now().date()
            consumo_diario = IAConsumptionLog.objects.filter(
                tenant_id=tenant_id,
                timestamp__date=hoje
            ).count()
            
            if consumo_diario >= quota.daily_limit:
                return {'status': 'error', 'erro': 'Limite diário de IA excedido.'}

        resultado = classificar_reclamacao(descricao=descricao, tipo_reclamacao=tipo_reclamacao)
        
        if 'erro' not in resultado:
            complaint = Complaint.objects.get(pk=complaint_id)
            complaint.ia_urgencia = resultado['urgencia']
            complaint.ia_sentimento = resultado['sentimento']
            complaint.ia_classificado_em = timezone.now()
            complaint.save(update_fields=['ia_urgencia', 'ia_sentimento', 'ia_classificado_em'])
            
            if tenant_id:
                IAConsumptionLog.objects.create(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    endpoint='classificar_reclamacao',
                    tokens_used=resultado.get('tokens', 0)
                )

        return resultado
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
