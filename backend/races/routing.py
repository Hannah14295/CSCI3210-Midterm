from django.urls import path

from .consumers import RaceConsumer

websocket_urlpatterns = [
    path("ws/races/<int:race_id>/", RaceConsumer.as_asgi()),
]
