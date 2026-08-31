from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        # Initialize Firebase Admin SDK when app is ready
        try:
            from .firebase_service import initialize_firebase
            initialize_firebase()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Firebase initialization skipped during startup: {e}")
