
import os
import django
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

from core.models import Store, StoreAudit

def test_monthly_count():
    print("Testing Monthly Audit Count Annotation...")
    
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    print(f"Start of month: {start_of_month}")

    # Simulate basic queryset
    stores_queryset = Store.objects.filter(active=True).order_by('code')
    print(f"Initial store count: {stores_queryset.count()}")

    # Apply annotation
    stores_queryset = stores_queryset.annotate(
        audits_this_month_count=Count(
            'audits', 
            filter=Q(audits__created_at__gte=start_of_month)
        )
    )

    # Convert to list to trigger query
    stores = list(stores_queryset[:10])
    
    print("\nResults:")
    for store in stores:
        print(f"Store: {store.code}, Audits Month: {getattr(store, 'audits_this_month_count', 'MISSING')}")

    # Check if any store has audits this month to verify positive cases
    stores_with_audits = stores_queryset.filter(audits_this_month_count__gt=0)
    print(f"\nStores with audits this month: {stores_with_audits.count()}")
    if stores_with_audits.exists():
        s = stores_with_audits.first()
        print(f"Example: {s.code} has {s.audits_this_month_count} audits")

if __name__ == '__main__':
    test_monthly_count()
