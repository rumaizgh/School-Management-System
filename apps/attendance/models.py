from django.db import models
from apps.account.models import UserData
from apps.subject.models import Subject
from django.utils import timezone



class Attendance(models.Model):
    student = models.ForeignKey(
        UserData, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'student'},
        related_name="attendances_as_student",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL, 
        null=True,
        related_name="attendances",
    )
    teacher = models.ForeignKey(
        UserData, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'teacher'},
        related_name="attendances_as_teacher", 
    )
    date = models.DateField(auto_now_add=True)  
    status = models.CharField(         
        max_length=10,
        choices=[
            ("present", "Present"),
            ("absent", "Absent"),
            ("late", "Late"),
            ("leave", "Leave"),
        ],
        default="present",
    )
    created_at = models.DateTimeField(default=timezone.now)  
    updated_at = models.DateTimeField(auto_now=True)   

    def __str__(self):
        return f"{self.student} - {self.subject} ({self.date})"