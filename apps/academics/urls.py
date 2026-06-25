from rest_framework.routers import DefaultRouter
from .views import CreateClass,ViewAllClassTeacher,ViewStudentsByClass,ViewTeachersByClass,TimeTablesView,PaymentListCreateAPIView,FeeListCreateAPIView,ViewFee,CreatePayment,ViewFeeByStudent,ExportFee,FeeExportPreview,SearchPaymentHistory,MarkListCreateAPIView,MarkUpdateAPIView,MarkByStudentAPIView,MarkBySubjectAPIView,InstituteView
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('institute/', InstituteView.as_view()),
    path('institute/<int:id>/', InstituteView.as_view()),
    path('class/teacher/', ViewAllClassTeacher.as_view()),
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
    path('class/students/<int:id>/', ViewStudentsByClass.as_view()),
    path('class/teachers/<int:id>/', ViewTeachersByClass.as_view()),
    path('payments/', PaymentListCreateAPIView.as_view()),
    path('fee/', FeeListCreateAPIView.as_view()),
    path('fee/<int:id>/', FeeListCreateAPIView.as_view()),
    path('fee/student/<int:student_id>/', ViewFeeByStudent.as_view()),
    path('fee/classs/<int:classs_id>/', ViewFee.as_view()),
    path('timetables/', TimeTablesView.as_view(), name='createtimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='updatetimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='deletetimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='viewonlyassignedteacherTT&studentcls'),
    path('payment/', CreatePayment.as_view(), name='createpayment'),
    path('payment/<int:student_id>/', CreatePayment.as_view(), name='getpayment'),
    path('export-fees/', ExportFee.as_view(), name='export-fees'),
    path('export-fees-preview/', FeeExportPreview.as_view(), name='export-fees-preview'),
    path('payment/search/', SearchPaymentHistory.as_view(), name='search-payment-history'),
    path('payment/search/<int:id>/', SearchPaymentHistory.as_view(), name='search-payment-history'),
    path('marks/', MarkListCreateAPIView.as_view(), name='marks-list-create'),
    path('marks/<int:id>/', MarkUpdateAPIView.as_view(), name='marks-update-delete'),
    path('marks/student/<int:student_id>/', MarkByStudentAPIView.as_view(), name='marks-by-student'),
    path('marks/subject/<int:subject_id>/', MarkBySubjectAPIView.as_view(), name='marks-by-subject'),
]