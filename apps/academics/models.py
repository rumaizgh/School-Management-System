from datetime import timezone
from django.db import models
from django.utils import timezone
from multiselectfield import MultiSelectField
from apps.account.models import UserData



class Batch(models.Model):

    classs = models.CharField(max_length=10)

    YEAR_CHOICES = [
        (f"{y}-{str(y+1)[-2:]}", f"{y}-{str(y+1)[-2:]}")
        for y in range(2020, 2050)
    ]

    year = models.CharField(
        max_length=7,
        choices=YEAR_CHOICES,
    )

    class Meta:
        unique_together = ['classs', 'year']

    def __str__(self):
        return f"{self.classs}{f' ({self.year})' if self.year else ''}"
 
class Fee(models.Model):
    student = models.ForeignKey(
        'account.UserData', 
        limit_choices_to={'user_type': 'student'}, 
        on_delete=models.CASCADE
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    paid_on = models.DateField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # If instance already exists, add to the existing paid_amount
        if self.pk:
            prev = Fee.objects.get(pk=self.pk)
            # If paid_amount is being updated (not initial assignment)
            if self.paid_amount != prev.paid_amount:
                self.paid_amount = prev.paid_amount + self.paid_amount

        # Always calculate balance
        self.balance_amount = self.amount - self.paid_amount

        if self.paid_amount >= self.amount:
            self.paid = True
            self.balance_amount = 0
            if not self.paid_on:
                self.paid_on = timezone.now().date()
        else:
            self.paid = False
            self.paid_on = None

        super().save(*args, **kwargs)

    
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

    classs = models.ForeignKey('academics.Batch', on_delete=models.CASCADE)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey(UserData, limit_choices_to={'user_type': 'teacher'}, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    day = MultiSelectField(choices=DAY_CHOICES)
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