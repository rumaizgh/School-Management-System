from django.urls import path
from .views import (
    SalaryConfigView,
    DisbursePaymentView,
    PayrollHistoryView,
    TeacherPaymentHistoryView,
)

urlpatterns = [
    # Salary configuration (create / update / retrieve)
    path('teachers/<int:teacher_id>/salary-config/', SalaryConfigView.as_view(),name='salary-config'),

    # Salary disbursement
    path('disburse/',DisbursePaymentView.as_view(),name='payroll-disburse'),

    # Institution-wide payroll history
    path('history/',PayrollHistoryView.as_view(),name='payroll-history'),

    # Per-teacher payment history (also exposed under /api/account/ in root urls)
    path('teachers/<int:teacher_id>/payments/',TeacherPaymentHistoryView.as_view(),name='teacher-payment-history'),
]
