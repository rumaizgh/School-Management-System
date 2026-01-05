from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceSessionCreate, AttendanceStudentsList, AttendanceRecordView, ViewAttendanceSessions

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('atdsessioncreate/', AttendanceSessionCreate.as_view(), name='atdsessioncreate'),
    path('viewsession/<int:id>/', ViewAttendanceSessions.as_view(), name='viewsession'),
    path('viewsession/', ViewAttendanceSessions.as_view(), name='viewsession'),
    path('liststudents/<int:id>/', AttendanceStudentsList.as_view(), name='liststudents'),
    path('showatdrec/<int:id>/', AttendanceRecordView.as_view(), name='showatdrec')
]
