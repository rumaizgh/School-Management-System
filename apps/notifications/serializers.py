from rest_framework import serializers
from .models import UserDevice, NotificationHistory


class DeviceTokenSerializer(serializers.Serializer):
    device_token = serializers.CharField(max_length=500, required=True)
    device_type = serializers.ChoiceField(choices=['android', 'ios'], default='android')


class NotificationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationHistory
        fields = ['id', 'title', 'body', 'type', 'is_read', 'created_at', 'data_payload']


class SendBroadcastSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=True)
    body = serializers.CharField(required=True)
    target_type = serializers.ChoiceField(
        choices=['all', 'class', 'section', 'user'],
        default='all'
    )
    target_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    data_payload = serializers.DictField(required=False, default=dict)
