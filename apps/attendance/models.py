from django.db import models
from apps.account.models import UserData
from apps.subject.models import Subject
from django.utils import timezone
from apps.academics.models import Batch, TimeTable

class AttendanceSession(models.Model):
    institute = models.ForeignKey('academics.Institute', on_delete=models.CASCADE, related_name='attendance_sessions', null=True, blank=True)
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
    end_time = models.TimeField(null=True, blank=True)
    is_exam = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(UserData, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_attendance_sessions')
    recorded_by_role = models.CharField(max_length=50, null=True, blank=True)
    is_substitution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def save(self, *args, **kwargs):
        if not self.institute:
            if self.teacher and self.teacher.institute:
                self.institute = self.teacher.institute
            elif self.classs and self.classs.institute:
                self.institute = self.classs.institute
            elif self.recorded_by and self.recorded_by.institute:
                self.institute = self.recorded_by.institute
        if self.timetable and hasattr(self.timetable, 'is_exam'):
            self.is_exam = self.timetable.is_exam
        super().save(*args, **kwargs)

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
    leave_reason = models.CharField(max_length=255, null=True, blank=True, default=None)
    is_excused = models.BooleanField(default=False)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student} - {self.session.date} - {self.status}"


class StudentLeaveRequest(models.Model):
    REASON_CHOICES = [
        ('sick', 'Sick'),
        ('medical', 'Medical'),
        ('family_function', 'Family Function'),
        ('travel', 'Travel'),
        ('exam_prep', 'Exam Prep'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    HALF_DAY_PERIOD_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
    ]

    student = models.ForeignKey(
        UserData,
        limit_choices_to={'user_type': 'student'},
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    institute = models.ForeignKey(
        'academics.Institute',
        on_delete=models.CASCADE,
        related_name='leave_requests',
        null=True,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=10,
        choices=HALF_DAY_PERIOD_CHOICES,
        null=True,
        blank=True
    )
    reason_category = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default='other'
    )
    reason_notes = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_remarks = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        UserData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leaves'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_leave_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'start_date', 'end_date'], name='idx_slr_student_dates'),
            models.Index(fields=['status', 'created_at'], name='idx_slr_status_created'),
            models.Index(fields=['start_date', 'end_date', 'status'], name='idx_slr_dates_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.institute and self.student and self.student.institute:
            self.institute = self.student.institute
        super().save(*args, **kwargs)

    @property
    def duration_days(self):
        if self.is_half_day:
            return 0.5
        if self.start_date and self.end_date:
            return float((self.end_date - self.start_date).days + 1)
        return 0.0

    @property
    def duration_label(self):
        if self.is_half_day:
            if self.half_day_period == 'morning':
                return "Half Day (Morning)"
            elif self.half_day_period == 'afternoon':
                return "Half Day (Afternoon)"
            return "Half Day"
        days = self.duration_days
        if days == 1.0:
            return "1 Day"
        return f"{int(days)} Days"

    @property
    def formatted_date_range(self):
        if not self.start_date or not self.end_date:
            return ""
        if self.start_date == self.end_date:
            return self.start_date.strftime("%d %b %Y")
        if self.start_date.month == self.end_date.month and self.start_date.year == self.end_date.year:
            return f"{self.start_date.strftime('%d')} - {self.end_date.strftime('%d %b %Y')}"
        if self.start_date.year == self.end_date.year:
            return f"{self.start_date.strftime('%d %b')} - {self.end_date.strftime('%d %b %Y')}"
        return f"{self.start_date.strftime('%d %b %Y')} - {self.end_date.strftime('%d %b %Y')}"

    @property
    def formatted_reason(self):
        cat_display = self.get_reason_category_display()
        if self.reason_notes and self.reason_notes.strip():
            return f"{cat_display}: {self.reason_notes.strip()}"
        return cat_display

    def __str__(self):
        return f"{self.student} - {self.formatted_date_range} ({self.status})"

