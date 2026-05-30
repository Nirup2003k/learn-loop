from django.urls import re_path

from core.consumers import VideoCallConsumer, ChatConsumer, NotificationConsumer


websocket_urlpatterns = [
    re_path(r'^ws/video/(?P<room_name>[^/]+)/$', VideoCallConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<user_id>\d+)/$', ChatConsumer.as_asgi()),
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]
