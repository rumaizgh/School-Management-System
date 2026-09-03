from django.db import models
from django.utils import timezone


class TeacherSalary(models.Model):
    """
    Master salary configuration for a teacher for a specific month.
    Supports both hourly and fixed-monthly pay types.
    Unique per (teacher, month) pair.
    """

    PAY_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('monthly', 'Monthly'),
    ]
    DEDUCTION_TYPE_CHOICES = [
        ('none', 'None'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    STATUS_CHOICES = [
        ('configured', 'Configured'),
        ('draft', 'Draft'),
    ]

    teacher = models.ForeignKey(
        'account.UserData',
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'teacher'},
        related_name='salary_configs'
    )
    institute = models.ForeignKey(
        'academics.Institute',
        on_delete=models.CASCADE,
        related_name='teacher_salaries',
        null=True,
        blank=True
    )
    month = models.CharField(max_length=7, help_text="Format: YYYY-MM")

    # Pay type & base amounts
    pay_type = models.CharField(max_length=10, choices=PAY_TYPE_CHOICES, default='monthly')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                        help_text="Rate per hour for hourly pay type")
    units_completed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                          help_text="Hours worked (for hourly pay type)")

    # Allowances & manual deductions
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                     help_text="Manual/other deductions")
    advance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unpaid_leave_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # PF configuration
    pf_type = models.CharField(max_length=12, choices=DEDUCTION_TYPE_CHOICES, default='none')
    pf_value = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                   help_text="Percentage or fixed amount for PF")

    # Tax configuration
    tax_type = models.CharField(max_length=12, choices=DEDUCTION_TYPE_CHOICES, default='none')
    tax_value = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                    help_text="Percentage or fixed amount for Tax")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='configured')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['teacher', 'month']
        ordering = ['-month', 'teacher__name']
        db_table = 'payroll_teacher_salary'

    def __str__(self):
        return f"{self.teacher.name} — {self.month} ({self.pay_type})"

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    @property
    def gross_salary(self):
        """Gross earnings before any deductions."""
        if self.pay_type == 'hourly':
            units = self.units_completed or 0
            return float(self.rate_per_unit) * float(units)
        return float(self.base_salary)

    @property
    def pf_deduction(self):
        gross = self.gross_salary
        if self.pf_type == 'percentage':
            return round(gross * float(self.pf_value) / 100, 2)
        elif self.pf_type == 'fixed':
            return float(self.pf_value)
        return 0.0

    @property
    def tax_deduction(self):
        gross = self.gross_salary
        if self.tax_type == 'percentage':
            return round(gross * float(self.tax_value) / 100, 2)
        elif self.tax_type == 'fixed':
            return float(self.tax_value)
        return 0.0

    @property
    def net_salary(self):
        """Final take-home after all deductions and allowances."""
        return round(
            self.gross_salary
            + float(self.allowances)
            - float(self.deductions)
            - self.pf_deduction
            - self.tax_deduction
            - float(self.advance_deduction)
            - float(self.unpaid_leave_deduction),
            2
        )

    @property
    def total_paid(self):
        return float(
            self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        )

    @property
    def balance(self):
        return round(self.net_salary - self.total_paid, 2)

    @property
    def payment_status(self):
        paid = self.total_paid
        net = self.net_salary
        if paid <= 0:
            return 'UNPAID'
        elif paid >= net:
            return 'FULL_PAID'
        return 'PARTIAL'


class SalaryPayment(models.Model):
    """
    Records a single salary disbursement transaction for a teacher.
    Multiple payments can be made against one TeacherSalary (partial payments).
    """

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    ]

    salary = models.ForeignKey(
        TeacherSalary,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    teacher = models.ForeignKey(
        'account.UserData',
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'teacher'},
        related_name='salary_payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=15,
        choices=PAYMENT_METHOD_CHOICES,
        default='bank_transfer'
    )
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    paid_on = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-paid_on']
        db_table = 'payroll_salary_payment'

    def __str__(self):
        return f"Payment #{self.id} — {self.teacher.name} — ₹{self.amount} ({self.salary.month})"
