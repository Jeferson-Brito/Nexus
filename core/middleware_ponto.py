"""
Middleware que redireciona o usuário do tipo 'tablet' exclusivamente
para a tela kiosk de registro de ponto.
"""
from django.shortcuts import redirect
from django.conf import settings


class TabletRedirectMiddleware:
    """
    Se o usuário logado tem role='tablet' e está tentando acessar
    qualquer URL que não seja /ponto/tablet/*, redireciona para o kiosk.
    """

    ALLOWED_TABLET_PREFIXES = [
        '/ponto/tablet/',
        '/api/ponto/',
        '/static/',
        '/media/',
        '/login/',
        '/logout/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'tablet'
        ):
            path = request.path
            allowed = any(path.startswith(prefix) for prefix in self.ALLOWED_TABLET_PREFIXES)
            if not allowed:
                return redirect('/ponto/tablet/')

        return self.get_response(request)
