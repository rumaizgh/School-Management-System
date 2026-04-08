from rest_framework.routers import DefaultRouter
from .views import CreateClass,ViewAllClassTeacher,ViewStudentsByClass,ViewTeachersByClass,TimeTablesView,PaymentListCreateAPIView,FeeListCreateAPIView,ViewFee
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('class/teacher/', ViewAllClassTeacher.as_view()),
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
    path('class/students/<int:id>/', ViewStudentsByClass.as_view()),
    path('class/teachers/<int:id>/', ViewTeachersByClass.as_view()),
    path('payments/', PaymentListCreateAPIView.as_view()),
    path('fee/', FeeListCreateAPIView.as_view()),
    path('fee/<int:id>/', FeeListCreateAPIView.as_view()),
    path('fee/classs/<int:classs_id>/', ViewFee.as_view()),
    path('timetables/', TimeTablesView.as_view(), name='createtimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='updatetimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='deletetimetable'),
    path('timetables/<int:id>/', TimeTablesView.as_view(), name='viewonlyassignedteacherTT&studentcls')

]