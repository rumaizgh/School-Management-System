from rest_framework import serializers
from .models import UserDevice, NotificationHistory


class DeviceTokenSerializer(serializers.Serializer):
    device_token = serializers.CharField(max_length=500, required=False)
    fcm_token = serializers.CharField(max_length=500, required=False)
    fcmToken = serializers.CharField(max_length=500, required=False)
    token = serializers.CharField(max_length=500, required=False)
    device_type = serializers.ChoiceField(choices=['android', 'ios'], default='android', required=False)

    def validate(self, attrs):
        token = (
            attrs.get('device_token')
            or attrs.get('fcm_token')
            or attrs.get('fcmToken')
            or attrs.get('token')
        )
        if not token:
            raise serializers.ValidationError({"device_token": "device_token or fcm_token is required."})
        attrs['device_token'] = token
        attrs.setdefault('device_type', 'android')
        return attrs


class NotificationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationHistory
        fields = [
            'id',
            'broadcast_id',
            'title',
            'body',
            'type',
            'is_read',
            'delivery_status',
            'delivered_at',
            'read_at',
            'created_at',
            'data_payload',
        ]


class SendBroadcastSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=True)
    body = serializers.CharField(required=True)
    type = serializers.CharField(required=False, default='general_announcement')
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

