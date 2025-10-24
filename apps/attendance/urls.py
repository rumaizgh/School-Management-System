from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceSessionViewSet, AtdSession

router = DefaultRouter()
router.register(r'attendance', AttendanceSessionViewSet, basename='attendance')
router.register(r'atd', AtdSession, basename='atd')

urlpatterns = [
    path('', include(router.urls)),
    path('atd/', AtdSession.as_view({'get': 'list'}), name='atd')
]
