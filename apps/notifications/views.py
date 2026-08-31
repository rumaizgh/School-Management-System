from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.db import models
from apps.account.models import UserData
from .models import UserDevice, NotificationHistory
from .serializers import (
    DeviceTokenSerializer,
    NotificationHistorySerializer,
    SendBroadcastSerializer
)
from .firebase_service import send_fcm_notification


class DeviceTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        device_token = serializer.validated_data['device_token']
        device_type = serializer.validated_data['device_type']

        # Update or create user device token
        UserDevice.objects.update_or_create(
            device_token=device_token,
            defaults={
                'user': request.user,
                'device_type': device_type,
            }
        )

        return Response(
            {
                "status": "success",
                "message": "Device token saved successfully."
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request):
        device_token = request.data.get('device_token')
        if not device_token:
            return Response(
                {"status": "error", "message": "device_token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted, _ = UserDevice.objects.filter(
            user=request.user,
            device_token=device_token
        ).delete()

        return Response(
            {
                "status": "success",
                "message": "Token deleted successfully."
            },
            status=status.HTTP_200_OK
        )


class NotificationHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        page_number = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 20)

        try:
            page_number = int(page_number)
            limit = int(limit)
        except ValueError:
            page_number = 1
            limit = 20

        notifications_qs = NotificationHistory.objects.filter(user=request.user)
        unread_count = notifications_qs.filter(is_read=False).count()

        paginator = Paginator(notifications_qs, limit)
        page_obj = paginator.get_page(page_number)

        serializer = NotificationHistorySerializer(page_obj.object_list, many=True)

        return Response(
            {
                "status": "success",
                "data": {
                    "unread_count": unread_count,
                    "notifications": serializer.data
                }
            },
            status=status.HTTP_200_OK
        )


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = NotificationHistory.objects.get(id=pk, user=request.user)
        except NotificationHistory.DoesNotExist:
            return Response(
                {"status": "error", "message": "Notification ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        notification.is_read = True
        notification.save()

        return Response(
            {
                "status": "success",
                "message": "Notification marked as read."
            },
            status=status.HTTP_200_OK
        )


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        NotificationHistory.objects.filter(user=request.user, is_read=False).update(is_read=True)

        return Response(
            {
                "status": "success",
                "message": "All notifications marked as read."
            },
            status=status.HTTP_200_OK
        )


class SendBroadcastView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Allow superadmin, admin, or staff
        if not (request.user.is_superuser or request.user.user_type in ['admin', 'superadmin'] or request.user.is_staff):
            return Response(
                {"status": "error", "message": "Permission denied. Administrators only."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SendBroadcastSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        title = serializer.validated_data['title']
        body = serializer.validated_data['body']
        target_type = serializer.validated_data['target_type']
        target_ids = serializer.validated_data['target_ids']
        data_payload = serializer.validated_data.get('data_payload', {})

        # Resolve target users
        target_users_qs = UserData.objects.all()

        # If admin belongs to an institute, filter users by institute
        if hasattr(request.user, 'institute') and request.user.institute:
            target_users_qs = target_users_qs.filter(
                models.Q(institute=request.user.institute) |
                models.Q(classs__institute=request.user.institute)
            ).distinct()

        if target_type in ['class', 'section']:
            if target_ids:
                target_users_qs = target_users_qs.filter(classs__id__in=target_ids).distinct()
        elif target_type == 'user':
            if target_ids:
                target_users_qs = target_users_qs.filter(id__in=target_ids).distinct()

        target_user_ids = list(target_users_qs.values_list('id', flat=True))

        screen = data_payload.get('screen')
        extra_data = {k: v for k, v in data_payload.items() if k != 'screen'}

        result = send_fcm_notification(
            user_ids=target_user_ids,
            title=title,
            body=body,
            notification_type='general_announcement',
            screen=screen,
            extra_data=extra_data,
            save_to_history=True
        )

        return Response(
            {
                "status": "success",
                "message": "Broadcast dispatched successfully.",
                "target_user_count": len(target_user_ids),
                "details": result
            },
            status=status.HTTP_200_OK
        )
