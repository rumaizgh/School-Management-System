import uuid
from django.db import models
from django.conf import settings


def generate_notif_id():
    return f"notif_{uuid.uuid4().hex[:12]}"


class UserDevice(models.Model):
    DEVICE_TYPE_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    device_token = models.CharField(max_length=500, unique=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES, default='android')
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_devices'
        ordering = ['-last_active']

    def __str__(self):
        return f"{self.user.name or self.user.email} - {self.device_type} ({self.device_token[:20]}...)"


class NotificationHistory(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_READ = 'READ'
    DELIVERY_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_READ, 'Read'),
    ]

    id = models.CharField(max_length=100, primary_key=True, default=generate_notif_id, editable=False)
    # Groups all per-recipient records that were sent from a single broadcast
    broadcast_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=150)
    body = models.TextField()
    type = models.CharField(max_length=50, default='general_announcement')
    is_read = models.BooleanField(default=False)
    delivery_status = models.CharField(
        max_length=10,
        choices=DELIVERY_STATUS_CHOICES,
        default=STATUS_PENDING
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    data_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'notification_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} -> {self.user.name or self.user.email} ({'Read' if self.is_read else 'Unread'})"
