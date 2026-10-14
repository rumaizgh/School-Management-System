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
    body = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, default='general_announcement')
    notification_type = serializers.CharField(required=False, allow_blank=True)
    target_type = serializers.ChoiceField(
        choices=[
            'all', 'class', 'section', 'user', 'role',
            'student', 'students', 'teacher', 'teachers'
        ],
        default='all',
        required=False
    )
    target_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    class_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    student_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    class_id = serializers.CharField(required=False, allow_null=True)
    student_id = serializers.CharField(required=False, allow_null=True)
    data_payload = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        # 1. Resolve body from aliases
        body = attrs.get('body') or attrs.get('message') or attrs.get('content')
        if not body:
            raise serializers.ValidationError({"body": "This field (or message/content) is required."})
        attrs['body'] = body

        # 2. Resolve type from alias
        notif_type = attrs.get('type') or attrs.get('notification_type') or 'general_announcement'
        attrs['type'] = notif_type

        # 3. Normalize target_type
        target_type = (attrs.get('target_type') or 'all').lower().strip()
        attrs['target_type'] = target_type

        # 4. Resolve target_ids from aliases
        raw_ids = list(attrs.get('target_ids') or [])
        if not raw_ids:
            if target_type == 'class' and attrs.get('class_ids'):
                raw_ids = list(attrs.get('class_ids'))
            elif target_type in ['student', 'students'] and attrs.get('student_ids'):
                raw_ids = list(attrs.get('student_ids'))
            elif attrs.get('student_ids'):
                raw_ids = list(attrs.get('student_ids'))
            elif attrs.get('class_ids'):
                raw_ids = list(attrs.get('class_ids'))

        if not raw_ids:
            if attrs.get('student_id'):
                raw_ids = [str(attrs['student_id'])]
            elif attrs.get('class_id'):
                raw_ids = [str(attrs['class_id'])]

        # Clean/convert target_ids elements to integers if numeric, else strings
        clean_ids = []
        for tid in raw_ids:
            if isinstance(tid, str) and tid.isdigit():
                clean_ids.append(int(tid))
            elif isinstance(tid, int):
                clean_ids.append(tid)
            elif tid:
                clean_ids.append(tid)
        attrs['target_ids'] = clean_ids

        return attrs


