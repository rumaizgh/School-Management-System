from django.db import models
from apps.account.models import UserData
from apps.subject.models import Subject
from django.utils import timezone
from apps.academics.models import Batch, TimeTable

class AttendanceSession(models.Model):
    teacher = models.ForeignKey(UserData, limit_choices_to={'user_type': 'teacher'}, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    classs = models.ForeignKey(Batch,  on_delete=models.CASCADE)
    timetable = models.ForeignKey(
        TimeTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )
    date = models.DateField(default=timezone.localdate)
    time = models.TimeField()

    def __str__(self):
        return f"{self.subject} - {self.date}"


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records"
    )
    student = models.ForeignKey(UserData, limit_choices_to={'user_type': 'student'}, on_delete=models.CASCADE)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default="absent")

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student} - {self.session.date} - {self.status}"
