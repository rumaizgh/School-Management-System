from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceSessionCreate, AttendanceStudentsList, AttendanceRecordView

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('atdsessioncreate/<int:id>/', AttendanceSessionCreate.as_view(), name='atdsessioncreate'),
    path('liststudents/<int:id>/', AttendanceStudentsList.as_view(), name='liststudents'),
    path('showatdrec/<int:id>/', AttendanceRecordView.as_view(), name='showatdrec')
]
