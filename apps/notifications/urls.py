from django.urls import path
from .views import (
    DeviceTokenView,
    NotificationHistoryView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    MarkNotificationDeliveredView,
    BroadcastStatusView,
    SendBroadcastView,
    DeleteNotificationView,
    DeleteBroadcastView,
)

urlpatterns = [
    # Device Token Endpoints
    path('device-token/', DeviceTokenView.as_view(), name='device-token'),

    # Notification History List
    path('history/', NotificationHistoryView.as_view(), name='notification-history'),

    # Mark Single Notification as Read
    path('history/<str:pk>/read/', MarkNotificationReadView.as_view(), name='mark-read'),

    # Mark Single Notification as Delivered (device background ping)
    path('<str:pk>/delivered/', MarkNotificationDeliveredView.as_view(), name='mark-delivered'),

    # Mark All Notifications as Read
    path('read-all/', MarkAllNotificationsReadView.as_view(), name='mark-all-read'),

    # Admin Broadcast Send Endpoint
    path('admin/send/', SendBroadcastView.as_view(), name='admin-broadcast'),

    # Admin Broadcast Delivery & Read Status
    path('broadcast/<str:broadcast_id>/status/', BroadcastStatusView.as_view(), name='broadcast-status'),

    # Delete a single notification (any authenticated user, own record only)
    path('<str:pk>/delete/', DeleteNotificationView.as_view(), name='delete-notification'),

    # Admin: Delete an entire broadcast by broadcast_id
    path('broadcast/<str:broadcast_id>/delete/', DeleteBroadcastView.as_view(), name='delete-broadcast'),
]
