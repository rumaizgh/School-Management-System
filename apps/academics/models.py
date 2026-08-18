from datetime import timezone
from django.db import models
from django.utils import timezone

class Institute(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    logo = models.ImageField(upload_to='institute_logos/')
    established_date = models.DateField()
    
    def __str__(self):
        return self.name

class Batch(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
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
        unique_together = ['institute', 'classs', 'year']

    def __str__(self):
        return f"{self.classs}{f' ({self.year})' if self.year else ''}"
 
class Fee(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='fees', null=True, blank=True)
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
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
    ]
    fee = models.ForeignKey(Fee, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash')
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

    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='timetables', null=True, blank=True)
    teacher = models.ForeignKey(
    "account.UserData",
    on_delete=models.SET_NULL,
    null=True,
    blank=True
    )
    classs = models.ForeignKey('academics.Batch', on_delete=models.CASCADE)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_exam = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"

class Exam(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    exam_name = models.CharField(max_length=100)
    batch = models.ForeignKey('academics.Batch', on_delete=models.CASCADE)
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    timetable = models.ForeignKey('academics.TimeTable', on_delete=models.CASCADE, null=True, blank=True, limit_choices_to={'is_exam': True})
    total_mark = models.DecimalField(max_digits=10, decimal_places=2)
    pass_mark = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    question_paper = models.FileField(upload_to='question_papers/', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ['exam_name', 'batch', 'subject']

    def __str__(self):
        return f"{self.exam_name} - {self.subject} ({self.batch})"

class Mark(models.Model):
    exam = models.ForeignKey('academics.Exam', on_delete=models.CASCADE, related_name='marks', null=True, blank=True)
    student = models.ForeignKey('account.UserData', on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='marks')
    obtained_mark = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, editable=False)

    @property
    def exam_name(self):
        return self.exam.exam_name if self.exam else ""

    @property
    def subject(self):
        return self.exam.subject if self.exam else None

    @property
    def batch(self):
        return self.exam.batch if self.exam else None

    @property
    def total_mark(self):
        return self.exam.total_mark if (self.exam and self.exam.total_mark) else None

    def save(self, *args, **kwargs):
        total = self.exam.total_mark if (self.exam and self.exam.total_mark) else None
        if total and total > 0:
            self.percentage = (self.obtained_mark / total) * 100
        else:
            self.percentage = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.exam_name} - {self.student.name} ({self.percentage}%)"