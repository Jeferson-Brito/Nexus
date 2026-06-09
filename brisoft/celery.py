import os
from celery import Celery
from django.conf import settings

# Define o módulo de configurações padrão do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brisoft.settings')

app = Celery('brisoft')

# Lê configurações do Django usando um namespace específico (ex: CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover de tasks em todas as apps registradas
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
