from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView,ViewAllTeachers, ViewAllStudents, UserDataView

router = DefaultRouter()
# router.register(r'users', UserDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('userdata/<int:id>/', UserDataView.as_view(), name='userdata'),

    path('login/', LoginView.as_view(), name='login'),

    path('teacher/<int:id>/', ViewAllTeachers.as_view(), name = 'teacher'),
    path('teachers/', ViewAllTeachers.as_view(), name='teachers'),

    path('student/<int:id>/', ViewAllStudents.as_view(), name='student'),
    path('students/', ViewAllStudents.as_view(), name='students')

]
