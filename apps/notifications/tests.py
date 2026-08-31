from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.account.models import UserData
from .models import UserDevice, NotificationHistory


class NotificationSystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test users
        self.student = UserData.objects.create_user(
            email="student@example.com",
            password="testpassword123",
            user_type="student",
            name="Student One"
        )
        self.admin = UserData.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword123",
            name="Admin User"
        )

    def test_register_device_token(self):
        self.client.force_authenticate(user=self.student)
        url = reverse('device-token')
        payload = {
            "device_token": "fcm_token_test_12345",
            "device_type": "android"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertTrue(UserDevice.objects.filter(device_token="fcm_token_test_12345", user=self.student).exists())

    def test_remove_device_token(self):
        self.client.force_authenticate(user=self.student)
        UserDevice.objects.create(
            user=self.student,
            device_token="fcm_token_delete_test",
            device_type="android"
        )
        url = reverse('device-token')
        payload = {"device_token": "fcm_token_delete_test"}
        response = self.client.delete(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserDevice.objects.filter(device_token="fcm_token_delete_test").exists())

    def test_retrieve_notification_history(self):
        self.client.force_authenticate(user=self.student)
        notif1 = NotificationHistory.objects.create(
            user=self.student,
            title="Test Exam",
            body="Exam is tomorrow",
            type="exam_alert",
            is_read=False
        )
        notif2 = NotificationHistory.objects.create(
            user=self.student,
            title="Fee Reminder",
            body="Fee due next week",
            type="fee_alert",
            is_read=True
        )

        url = reverse('notification-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['data']['unread_count'], 1)
        self.assertEqual(len(response.data['data']['notifications']), 2)

    def test_mark_single_notification_read(self):
        self.client.force_authenticate(user=self.student)
        notif = NotificationHistory.objects.create(
            user=self.student,
            title="Test Exam",
            body="Exam tomorrow",
            is_read=False
        )
        url = reverse('mark-read', kwargs={'pk': notif.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_notifications_read(self):
        self.client.force_authenticate(user=self.student)
        NotificationHistory.objects.create(user=self.student, title="A", body="A", is_read=False)
        NotificationHistory.objects.create(user=self.student, title="B", body="B", is_read=False)

        url = reverse('mark-all-read')
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(NotificationHistory.objects.filter(user=self.student, is_read=False).count(), 0)

    def test_admin_send_broadcast(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-broadcast')
        payload = {
            "title": "Holiday Announcement",
            "body": "School is closed tomorrow due to heavy rain.",
            "target_type": "all",
            "data_payload": {"screen": "holiday_calendar"}
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        # Check that NotificationHistory entries were created for all users
        self.assertEqual(NotificationHistory.objects.filter(title="Holiday Announcement").count(), 2)
