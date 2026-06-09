"""
URL configuration for brisoft project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import JsonResponse

def health_check(request):
    """Lightweight health check - no DB access"""
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

# Serve media files in both development and production
# In production, this is a fallback - consider using S3/Cloudinary for better performance
re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

# Also add to urlpatterns list
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
