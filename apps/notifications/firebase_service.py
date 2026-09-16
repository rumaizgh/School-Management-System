import os
import uuid
import logging
from django.conf import settings
from django.db import models
from django.utils import timezone
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None

logger = logging.getLogger(__name__)

_firebase_initialized = False


def initialize_firebase():
    global _firebase_initialized
    if not firebase_admin:
        return
    if _firebase_initialized or (firebase_admin and firebase_admin._apps):
        _firebase_initialized = True
        return

    cred_path = getattr(
        settings,
        'FIREBASE_CREDENTIALS_PATH',
        os.path.join(settings.BASE_DIR, 'config', 'firebase_credentials.json')
    )

    if os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
    else:
        logger.warning(f"Firebase credentials file not found at: {cred_path}")


def send_fcm_notification(
    user_ids,
    title,
    body,
    notification_type='general_announcement',
    screen=None,
    extra_data=None,
    save_to_history=True,
    sender_user_id=None
):
    """
    Sends FCM Push Notifications to devices associated with user_ids
    and optionally logs the notification in NotificationHistory.
    If sender_user_id is provided:
      - The sender is excluded from receiving the FCM push notification popup.
      - The sender's NotificationHistory record is automatically created as READ.
    """
    from .models import UserDevice, NotificationHistory
    from apps.account.models import UserData

    initialize_firebase()

    if isinstance(user_ids, (int, str)):
        user_ids = [user_ids]

    # 1. Save to NotificationHistory for in-app notification center
    saved_history_records = []
    broadcast_id = f"notif_{uuid.uuid4().hex[:12]}"
    if save_to_history and user_ids:
        data_payload = {}
        if screen:
            data_payload['screen'] = str(screen)
        if extra_data:
            for k, v in extra_data.items():
                data_payload[str(k)] = str(v)

        target_users = UserData.objects.filter(id__in=user_ids, is_active=True)
        now = timezone.now()

        # Identify logged-in users (have registered devices or last_login is set)
        logged_in_user_ids = set(
            UserData.objects.filter(id__in=user_ids, is_active=True)
            .filter(models.Q(devices__isnull=False) | models.Q(last_login__isnull=False))
            .values_list('id', flat=True)
        )

        history_objects = []
        for user in target_users:
            if user.id == sender_user_id:
                notif_status = NotificationHistory.STATUS_READ
                is_read = True
                delivered_at = now
                read_at = now
            elif user.id in logged_in_user_ids:
                notif_status = NotificationHistory.STATUS_DELIVERED
                is_read = False
                delivered_at = now
                read_at = None
            else:
                notif_status = NotificationHistory.STATUS_PENDING
                is_read = False
                delivered_at = None
                read_at = None

            history_objects.append(
                NotificationHistory(
                    user=user,
                    title=title,
                    body=body,
                    type=notification_type,
                    broadcast_id=broadcast_id,
                    data_payload=data_payload,
                    is_read=is_read,
                    delivery_status=notif_status,
                    delivered_at=delivered_at,
                    read_at=read_at,
                )
            )
        if history_objects:
            saved_history_records = NotificationHistory.objects.bulk_create(history_objects)

    # 2. Fetch device tokens (active users only)
    devices = UserDevice.objects.filter(user_id__in=user_ids, user__is_active=True)
    # Exclude sender from receiving FCM push notification popup
    if sender_user_id:
        devices = devices.exclude(user_id=sender_user_id)
    if not devices.exists():
        logger.info(f"No active device tokens found for user_ids: {user_ids}")
        return {
            "broadcast_id": broadcast_id,
            "success_count": 0,
            "failure_count": 0,
            "history_created": len(saved_history_records)
        }



    tokens_list = list(devices.values_list('device_token', flat=True))

    # Construct FCM data map (FCM data payload values MUST be strings)
    # Including title, body, and type directly in data helps Flutter foreground/background listeners
    fcm_data = {
        "click_action": "FLUTTER_NOTIFICATION_CLICK",
        "title": str(title),
        "body": str(body),
        "notification_type": str(notification_type),
        "broadcast_id": str(broadcast_id),
    }
    if screen:
        fcm_data["screen"] = str(screen)
    if extra_data:
        for k, v in extra_data.items():
            fcm_data[str(k)] = str(v)

    # Construct Multicast Message with high priority, sound, and channel configuration
    message = messaging.MulticastMessage(
        tokens=tokens_list,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=fcm_data,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="school_high_importance_channel",
                priority="high",
                sound="default",
                default_sound=True,
                default_vibrate_timings=True,
                default_light_settings=True,
                visibility="public",
                click_action="FLUTTER_NOTIFICATION_CLICK",
            )
        ),
        apns=messaging.APNSConfig(
            headers={
                "apns-priority": "10",
                "apns-push-type": "alert",
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound="default",
                    badge=1,
                    content_available=True,
                )
            )
        )
    )


    success_count = 0
    failure_count = 0

    try:
        response = messaging.send_each_for_multicast(message)
        success_count = response.success_count
        failure_count = response.failure_count

        logger.info(
            f"[FCM] Dispatched broadcast {broadcast_id}: {success_count} succeeded, "
            f"{failure_count} failed out of {len(tokens_list)} token(s)."
        )

        # Log details & clean up unregistered tokens
        if failure_count > 0:
            failed_tokens = []
            unregistered_codes = {
                "UNREGISTERED",
                "NOT_FOUND",
                "messaging/registration-token-not-registered",
                "NotRegistered",
            }
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    err = resp.exception
                    err_code = getattr(err, 'code', '') or ''
                    err_str = str(err)
                    token_preview = f"{tokens_list[idx][:15]}...{tokens_list[idx][-10:]}"
                    logger.warning(
                        f"[FCM] Token failure [{token_preview}]: code={err_code}, error={err_str}"
                    )
                    # Clean up ONLY if definitively unregistered/not found
                    if err_code in unregistered_codes or "notregistered" in err_str.lower() or "not registered" in err_str.lower():
                        failed_tokens.append(tokens_list[idx])

            if failed_tokens:
                deleted_count = UserDevice.objects.filter(device_token__in=failed_tokens).delete()[0]
                logger.info(f"[FCM] Cleaned up {deleted_count} unregistered FCM tokens from database.")

    except Exception as e:
        logger.error(f"[FCM] Error dispatching FCM message: {e}", exc_info=True)

    return {
        "broadcast_id": broadcast_id,
        "success_count": success_count,
        "failure_count": failure_count,
        "history_created": len(saved_history_records)
    }

