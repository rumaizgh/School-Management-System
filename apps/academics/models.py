from datetime import timezone
from django.db import models
from django.utils import timezone
from apps.account.models import UserData

class Batch(models.Model):

    batch = models.CharField(max_length=10)

    YEAR_CHOICES = [
        (f"{y}-{str(y+1)[-2:]}", f"{y}-{str(y+1)[-2:]}")
        for y in range(2020, 2050)
    ]

    year = models.CharField(
        max_length=7,
        choices=YEAR_CHOICES,
    )

    class Meta:
        unique_together = ['batch', 'year']

    def __str__(self):
        return f"{self.batch}{f' ({self.year})' if self.year else ''}"
 
class Fee(models.Model):
    student = models.ForeignKey('account.UserData', on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()

    def total_paid(self):
        return sum(p.amount for p in self.payments.all())

    def balance(self):
        return self.amount - self.total_paid()

    def is_paid(self):
        return self.total_paid() >= self.amount
    
class Payment(models.Model):
    fee = models.ForeignKey(Fee, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateField(auto_now_add=True)
    
class TimeTable(models.Model):

    DAY_CHOICES = [
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday')
    ]

    teacher = models.ForeignKey(UserData, limit_choices_to={'user_type': 'teacher'}, on_delete=models.CASCADE)
    batch = models.ForeignKey('academics.Batch', on_delete=models.CASCADE)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=['teacher', 'day', 'start_time'],
    #             name='unique_teacher_schedule'
    #         ),
    #         models.UniqueConstraint(
    #             fields=['batch', 'day', 'start_time'],
    #             name='unique_batch_schedule'
    #         ),
    #     ]

    #     ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"