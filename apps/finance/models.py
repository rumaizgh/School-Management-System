from django.db import models


class InstitutionalTransaction(models.Model):
    """
    Tracks non-student fee income and non-payroll expenses for the institution
    (e.g., stationery, utilities, maintenance, lab supplies, canteen rent, donations).
    """

    TYPE_CHOICES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Cheque'),
    ]

    CATEGORY_CHOICES = [
        # Expenses
        ('stationery', 'Stationery'),
        ('utilities', 'Utilities & Internet'),
        ('maintenance', 'Maintenance & Repairs'),
        ('lab_supplies', 'Lab Supplies'),
        ('event', 'Events & Functions'),
        # Incomes
        ('canteen_rent', 'Canteen Rent'),
        ('donation', 'Donations & Grants'),
        ('fine', 'Fines & Penalties'),
        # Either
        ('miscellaneous', 'Miscellaneous'),
    ]

    institute = models.ForeignKey(
        'academics.Institute',
        on_delete=models.CASCADE,
        db_column='institution_id',
        related_name='institutional_transactions',
        help_text="School/Institution identifier for multi-tenant isolation"
    )
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        help_text="'expense' or 'income'"
    )
    title = models.CharField(
        max_length=255,
        help_text="Particulars / Item name (e.g., Exam Pens, Pencils & Answer Sheets)"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Exact monetary amount"
    )
    category = models.CharField(
        max_length=50,
        help_text="Category key (e.g., stationery, utilities, maintenance, canteen_rent)"
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Payment mode: 'cash', 'upi', 'bank_transfer', 'check'"
    )
    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Optional UPI ID, Bank UTR, or Cheque number"
    )
    reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Optional Bill / Voucher / Invoice number (e.g. 'BILL-0982')"
    )
    remarks = models.TextField(
        null=True,
        blank=True,
        help_text="Optional notes or description"
    )
    date = models.DateTimeField(
        help_text="Transaction timestamp (UTC / timezone)"
    )
    is_edited = models.BooleanField(
        default=False,
        help_text="Default false. Automatically set to true when edited"
    )
    created_by = models.ForeignKey(
        'account.UserData',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_institutional_transactions',
        help_text="Admin user who created the record"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'institutional_transactions'
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['institute', 'type', 'date']),
            models.Index(fields=['institute', 'category']),
        ]

    def __str__(self):
        return f"[{self.type.upper()}] {self.title} - ₹{self.amount} ({self.date.strftime('%Y-%m-%d')})"

    @property
    def formatted_id(self):
        return f"tx-{self.id}"
