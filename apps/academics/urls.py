from rest_framework.routers import DefaultRouter
from .views import CreateClass,ViewAllClassTeacher,ViewStudentsByClass,ViewTeachersByClass,TimeTablesView,PaymentListCreateAPIView,FeeListCreateAPIView,ViewFee,CreatePayment,ViewFeeByStudent,LatestAssignedFeesAPIView,ExportFee,FeeExportPreview,ExportMark,MarkExportPreview,SearchPaymentHistory,MarkListCreateAPIView,MarkUpdateAPIView,MarkByStudentAPIView,MarkBySubjectAPIView,InstituteView, ExamListCreateAPIView, ExamAnalyticsAPIView, ExamMarksAPIView, StudentExamListAPIView, StudentExamAnalyticsAPIView, PayrollViewSet
from django.urls import path, include, re_path

router = DefaultRouter()
router.register(r'payrolls', PayrollViewSet, basename='payrolls')

urlpatterns = [
    path('', include(router.urls)),
    path('institute/', InstituteView.as_view()),
    path('institute/<int:id>/', InstituteView.as_view()),
    path('class/teacher/', ViewAllClassTeacher.as_view()),
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
    path('class/students/<int:id>/', ViewStudentsByClass.as_view()),
    path('class/teachers/<int:id>/', ViewTeachersByClass.as_view()),
    path('payments/', PaymentListCreateAPIView.as_view()),
    path('fee/', FeeListCreateAPIView.as_view()),
    path('fee/latest/', LatestAssignedFeesAPIView.as_view(), name='latest-assigned-fees'),
    path('fee/<int:id>/', FeeListCreateAPIView.as_view()),
    path('fee/student/<int:student_id>/', ViewFeeByStudent.as_view()),
    path('fee/classs/<int:classs_id>/', ViewFee.as_view()),
    path('timetables/', TimeTablesView.as_view(), name='createtimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='timetable-detail'),
    path('payment/', CreatePayment.as_view(), name='createpayment'),
    path('payment/<int:student_id>/', CreatePayment.as_view(), name='getpayment'),
    path('export-fees/', ExportFee.as_view(), name='export-fees'),
    path('export-fees-preview/', FeeExportPreview.as_view(), name='export-fees-preview'),
    path('export-marks/', ExportMark.as_view(), name='export-marks'),
    path('export-marks-preview/', MarkExportPreview.as_view(), name='export-marks-preview'),
    path('payment/search/', SearchPaymentHistory.as_view(), name='search-payment-history'),
    path('payment/search/<int:id>/', SearchPaymentHistory.as_view(), name='search-payment-history'),
    path('marks/', MarkListCreateAPIView.as_view(), name='marks-list-create'),
    path('marks/<int:id>/', MarkUpdateAPIView.as_view(), name='marks-update-delete'),
    path('marks/student/<int:student_id>/', MarkByStudentAPIView.as_view(), name='marks-by-student'),
    path('marks/subject/<int:subject_id>/', MarkBySubjectAPIView.as_view(), name='marks-by-subject'),
    path('exams/student/me/', StudentExamListAPIView.as_view(), name='student-exam-list'),
    path('exams/student/me/<int:exam_id>/analytics/', StudentExamAnalyticsAPIView.as_view(), name='student-exam-analytics'),
    path('exams/', ExamListCreateAPIView.as_view(), name='exam-list-create'),
    path('exams/<int:id>/', ExamListCreateAPIView.as_view(), name='exam-CRUD'),
    path('exams/<int:exam_id>/analytics/', ExamAnalyticsAPIView.as_view(), name='exam-analytics'),
    path('exams/<int:exam_id>/marks/', ExamMarksAPIView.as_view(), name='exam-marks-list'),
    path('exams/<int:exam_id>/marks/bulk/', ExamMarksAPIView.as_view(), name='exam-marks-bulk'),
    path('exams/<int:exam_id>/export/', ExportMark.as_view(), name='exam-export-marks'),
]