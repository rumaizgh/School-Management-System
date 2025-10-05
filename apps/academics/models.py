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
