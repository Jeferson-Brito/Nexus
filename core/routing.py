from django.urls import path
from core.consumers import CameraSignalingConsumer

websocket_urlpatterns = [
    path('ws/camera/', CameraSignalingConsumer.as_asgi()),
]
