import os
import logging
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_initialized = False


def initialize_firebase():
    global _firebase_initialized
    if _firebase_initialized or firebase_admin._apps:
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
    save_to_history=True
):
    """
    Sends FCM Push Notifications to devices associated with user_ids
    and optionally logs the notification in NotificationHistory.
    """
    from .models import UserDevice, NotificationHistory
    from apps.account.models import UserData

    initialize_firebase()

    if isinstance(user_ids, (int, str)):
        user_ids = [user_ids]

    # 1. Save to NotificationHistory for in-app notification center
    saved_history_records = []
    if save_to_history and user_ids:
        data_payload = {}
        if screen:
            data_payload['screen'] = str(screen)
        if extra_data:
            for k, v in extra_data.items():
                data_payload[str(k)] = str(v)

        target_users = UserData.objects.filter(id__in=user_ids)
        history_objects = [
            NotificationHistory(
                user=user,
                title=title,
                body=body,
                type=notification_type,
                data_payload=data_payload
            )
            for user in target_users
        ]
        if history_objects:
            saved_history_records = NotificationHistory.objects.bulk_create(history_objects)

    # 2. Fetch device tokens
    devices = UserDevice.objects.filter(user_id__in=user_ids)
    if not devices.exists():
        logger.info(f"No active device tokens found for user_ids: {user_ids}")
        return {"success_count": 0, "failure_count": 0, "history_created": len(saved_history_records)}

    tokens_list = list(devices.values_list('device_token', flat=True))

    # Construct FCM data map (FCM data payload values MUST be string)
    fcm_data = {"click_action": "FLUTTER_NOTIFICATION_CLICK"}
    if screen:
        fcm_data["screen"] = str(screen)
    if extra_data:
        for k, v in extra_data.items():
            fcm_data[str(k)] = str(v)

    # Construct Multicast Message
    message = messaging.MulticastMessage(
        tokens=tokens_list,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=fcm_data,
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                channel_id="school_high_importance_channel"
            )
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default",
                    badge=1
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

        # Clean up invalid/unregistered tokens
        if failure_count > 0:
            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    err_code = resp.exception.code if resp.exception else ""
                    if err_code in ["UNREGISTERED", "INVALID_ARGUMENT"] or "not registered" in str(resp.exception).lower():
                        failed_tokens.append(tokens_list[idx])
            
            if failed_tokens:
                deleted_count = UserDevice.objects.filter(device_token__in=failed_tokens).delete()[0]
                logger.info(f"Cleaned up {deleted_count} invalid FCM tokens from database.")

    except Exception as e:
        logger.error(f"Error dispatching FCM message: {e}")

    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "history_created": len(saved_history_records)
    }
