from django.db import models
from apps.account.models import UserData 

class Subject(models.Model):
    subject_name = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=10, unique=True)
    teacher = models.ForeignKey(
        UserData, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'user_type': 'teacher'},
        related_name='subjects'
    )

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"
    