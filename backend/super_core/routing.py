"""
WebSocket URL routing for real-time features
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/orders/(?P<order_id>\w+)/$', consumers.OrderTrackingConsumer.as_asgi()),
    re_path(r'ws/dispatch/(?P<rider_id>\w+)/$', consumers.DispatchConsumer.as_asgi()),
    re_path(r'ws/support/(?P<ticket_id>\w+)/$', consumers.SupportConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<user_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),
]