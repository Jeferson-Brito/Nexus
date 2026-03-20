from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def under_development(request, page_name='Página', description=None):
    return render(request, 'core/under_development.html', {
        'page_name': page_name,
        'description': description
    })
