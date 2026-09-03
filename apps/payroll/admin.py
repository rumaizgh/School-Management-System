from django.contrib import admin
from .models import TeacherSalary, SalaryPayment


@admin.register(TeacherSalary)
class TeacherSalaryAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'institute', 'month', 'pay_type', 'status', 'created_at']
    ordering = ['-month', 'teacher__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'teacher', 'salary', 'amount', 'payment_method', 'transaction_id', 'paid_on']
    ordering = ['-paid_on']
