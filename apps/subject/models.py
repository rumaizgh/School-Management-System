from django.db import models
from apps.account.models import UserData 
from apps.academics.models import Batch


class Subject(models.Model):
    institute = models.ForeignKey('academics.Institute', on_delete=models.CASCADE, related_name='subjects', null=True, blank=True)
    subject_name = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=10)
    teacher = models.ForeignKey(
        UserData, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'teacher'},
        related_name='subjects'
    )
    classs = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        null=True,
        related_name="subjects"
    )

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"


class Chapter(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    chapter_number = models.IntegerField()
    chapter_title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    target_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    reminder_enabled = models.BooleanField(default=True)
    reminder_days_before = models.IntegerField(default=2)
    notify_students_on_completion = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['chapter_number']
        unique_together = ['subject', 'chapter_number']

    def __str__(self):
        return f"Ch {self.chapter_number}: {self.chapter_title} ({self.subject.subject_name})"

    @property
    def completion_percentage(self):
        topics = self.topics.all()
        total_topics = topics.count()
        if total_topics > 0:
            completed_count = topics.filter(is_completed=True).count()
            val = (completed_count / total_topics) * 100
            return round(val, 1)
        return 100.0 if self.status == 'completed' else 0.0


class Topic(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.chapter.chapter_title}"