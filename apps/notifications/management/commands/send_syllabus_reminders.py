from django.core.management.base import BaseCommand
from apps.notifications.services import send_syllabus_due_reminders


class Command(BaseCommand):
    help = "Dispatches daily FCM push notification reminders to teachers for chapters due soon."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting syllabus due date reminders job..."))
        reminders_sent = send_syllabus_due_reminders()
        self.stdout.write(
            self.style.SUCCESS(f"Syllabus due date reminders job completed. Sent {reminders_sent} reminder notification(s).")
        )
