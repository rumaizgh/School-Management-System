from django.urls import path
from .views import AdminOverviewReportView, TeacherReportView, StudentReportView

urlpatterns = [
    path('admin/overview/', AdminOverviewReportView.as_view(), name='report-admin-overview'),
    path('teacher/<int:teacher_id>/', TeacherReportView.as_view(), name='report-teacher'),
    path('student/<int:student_id>/', StudentReportView.as_view(), name='report-student'),
]
