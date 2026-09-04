from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from apps.account.models import UserData
from apps.account.pagination import CustomPagination
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
        notifications_qs = NotificationHistory.objects.filter(user=request.user)
        unread_count = notifications_qs.filter(is_read=False).count()

        notif_type = request.query_params.get('type')
        if notif_type:
            notifications_qs = notifications_qs.filter(type=notif_type.strip())

        paginator = CustomPagination()
        paginated_qs = paginator.paginate_queryset(notifications_qs, request)
        serializer = NotificationHistorySerializer(paginated_qs, many=True)

        response = paginator.get_paginated_response(serializer.data)
        response.data['unread_count'] = unread_count
        return response


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

        now = timezone.now()
        notification.is_read = True
        notification.delivery_status = NotificationHistory.STATUS_READ
        if not notification.read_at:
            notification.read_at = now
        # Ensure delivered_at is also set if somehow missed
        if not notification.delivered_at:
            notification.delivered_at = now
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
        now = timezone.now()
        NotificationHistory.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            delivery_status=NotificationHistory.STATUS_READ,
            read_at=now
        )

        return Response(
            {
                "status": "success",
                "message": "All notifications marked as read."
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Mark notification as delivered (device background ping)
# POST /api/notifications/{notification_id}/delivered/
# ─────────────────────────────────────────────────────────────────────────────
class MarkNotificationDeliveredView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = NotificationHistory.objects.get(id=pk, user=request.user)
        except NotificationHistory.DoesNotExist:
            return Response(
                {"status": "error", "message": "Notification ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only update if not already READ (don't downgrade status)
        if notification.delivery_status == NotificationHistory.STATUS_PENDING:
            notification.delivery_status = NotificationHistory.STATUS_DELIVERED
            notification.delivered_at = timezone.now()
            notification.save()

        return Response(
            {
                "status": "success",
                "message": "Notification marked as delivered."
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Broadcast Delivery & Read Status (Admin only)
# GET /api/notifications/broadcast/{broadcast_id}/status/
# ─────────────────────────────────────────────────────────────────────────────
class BroadcastStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, broadcast_id):
        # Admin-only guard
        if not (request.user.is_superuser or request.user.user_type in ['admin', 'superadmin'] or request.user.is_staff):
            return Response(
                {"status": "error", "message": "Permission denied. Administrators only."},
                status=status.HTTP_403_FORBIDDEN
            )

        records = NotificationHistory.objects.filter(
            broadcast_id=broadcast_id
        ).select_related('user')

        if not records.exists():
            return Response(
                {"status": "error", "message": "Broadcast ID not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Grab meta from the first record (all share title/body/sent_at)
        first = records.first()

        total = records.count()
        read_count = records.filter(delivery_status=NotificationHistory.STATUS_READ).count()
        delivered_count = records.filter(delivery_status=NotificationHistory.STATUS_DELIVERED).count()
        pending_count = records.filter(delivery_status=NotificationHistory.STATUS_PENDING).count()

        recipients = []
        for rec in records.order_by('created_at'):
            user = rec.user
            # Resolve class name (students have a classs M2M; teachers/admins may not)
            class_name = None
            if user.user_type == 'student':
                batch = user.classs.first()
                if batch:
                    class_name = str(batch)

            recipients.append({
                "user_id": user.id,
                "user_name": user.name or user.email,
                "role": user.user_type.capitalize(),
                "class_name": class_name,
                "status": rec.delivery_status,
                "delivered_at": rec.delivered_at.isoformat() if rec.delivered_at else None,
                "read_at": rec.read_at.isoformat() if rec.read_at else None,
            })

        return Response(
            {
                "status": "success",
                "data": {
                    "broadcast_id": broadcast_id,
                    "title": first.title,
                    "body": first.body,
                    "sent_at": first.created_at.isoformat(),
                    "total_targeted": total,
                    "read_count": read_count,
                    "delivered_count": delivered_count,
                    "pending_count": pending_count,
                    "recipients": recipients,
                }
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
        notif_type = serializer.validated_data.get('type')
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
            notification_type=notif_type,
            screen=screen,
            extra_data=extra_data,
            save_to_history=True
        )

        return Response(
            {
                "status": "success",
                "message": "Broadcast dispatched successfully.",
                "broadcast_id": result.get("broadcast_id"),
                "target_user_count": len(target_user_ids),
                "details": result
            },
            status=status.HTTP_200_OK
        )
