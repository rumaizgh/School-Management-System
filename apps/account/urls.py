from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView,ViewAllTeachers,UserDataViewSet,ViewAllStudents

router = DefaultRouter()
router.register(r'users', UserDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('teachers/', ViewAllTeachers.as_view(), name='teachers'),
    path('students/', ViewAllTeachers.as_view(), name='students'),

]
