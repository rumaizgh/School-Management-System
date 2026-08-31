from django.contrib import admin
from .models import UserDevice, NotificationHistory


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'device_type', 'device_token_short', 'created_at', 'last_active']

    def device_token_short(self, obj):
        return f"{obj.device_token[:30]}..." if obj.device_token else ""
    device_token_short.short_description = "Device Token"


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'type', 'is_read', 'created_at']

