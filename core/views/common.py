from django.http import JsonResponse
from django.utils import timezone

@login_required
def under_development(request, page_name='Página', description=None):
    return render(request, 'core/under_development.html', {
        'page_name': page_name,
        'description': description
    })

def api_ping(request):
    return JsonResponse({
        'status': 'ok', 
        'timestamp': timezone.now().isoformat(),
        'service': 'Nexus'
    })
