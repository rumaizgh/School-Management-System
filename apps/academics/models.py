from datetime import timezone
from django.db import models
from django.utils import timezone


class Batch(models.Model):
    CLASS_CHOICES = [
        ('plus_one', 'Plus One'),
        ('plus_two', 'Plus Two'),
    ]
    name = models.CharField(max_length=50, choices=CLASS_CHOICES)
    year = models.IntegerField()

    section = models.CharField(max_length=10, blank=True, null=True)  

    def __str__(self):
        return f"{self.get_name_display()} - {self.year}{f' ({self.section})' if self.section else ''}"
 
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
        # Automatically update paid status
        if self.paid_amount >= self.amount:
            self.paid = True
            if not self.paid_on:
                self.paid_on = timezone.now().date()  # Set current date when fully paid
        else:
            self.paid = False
            self.balance_amount = self.amount - self.paid_amount
            self.paid_on = None  # Clear paid_on if not fully paid
        super().save(*args, **kwargs)
