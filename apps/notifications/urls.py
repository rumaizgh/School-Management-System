from django.urls import path
from .views import (
    DeviceTokenView,
    NotificationHistoryView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    SendBroadcastView,
)

urlpatterns = [
    # Device Token Endpoints
    path('device-token/', DeviceTokenView.as_view(), name='device-token'),

    # Notification History List
    path('history/', NotificationHistoryView.as_view(), name='notification-history'),

    # Mark Notification as Read
    path('<str:pk>/read/', MarkNotificationReadView.as_view(), name='mark-read'),

    # Mark All Notifications as Read
    path('read-all/', MarkAllNotificationsReadView.as_view(), name='mark-all-read'),

    # Admin Broadcast Endpoint
    path('admin/send/', SendBroadcastView.as_view(), name='admin-broadcast'),
]
