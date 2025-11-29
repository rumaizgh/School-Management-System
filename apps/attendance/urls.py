from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AtdSession, AtdSessionStart, AttendanceTake, AttendanceRecordViewSet
from .views import AttendanceSessionViewSet

router = DefaultRouter()
router.register(r'attendance', AttendanceSessionViewSet, basename='attendance')
router.register(r'atd', AtdSession, basename='atd')

urlpatterns = [
    path('', include(router.urls)),
    path('atd/', AtdSession.as_view({'get': 'list'}), name='atd'),
    path('atdstart/', AtdSessionStart.as_view({'post': 'create'}), name='atdstart'),
    path('atdtake/<int:batch_id>/', AttendanceTake.as_view({'get': 'list'}), name='atdtake'),
    path('atdcreate/', AttendanceRecordViewSet.as_view({'post': 'create'}), name='atdcreate'),
]
