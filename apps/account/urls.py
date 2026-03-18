from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView,ViewAllTeachers, ViewAllStudents, CreateStudent, CreateTeacher

router = DefaultRouter()
# router.register(r'users', UserDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # path('userdata/', UserDataView.as_view(), name='userdata'),
    # path('userdata/<int:id>/', UserDataView.as_view(), name='userdata'),

    path('login/', LoginView.as_view(), name='login'),

    path('teacher/<int:id>/', ViewAllTeachers.as_view(), name = 'teacher'),
    path('teachers/', ViewAllTeachers.as_view(), name='teachers'),

    path('student/<int:id>/', ViewAllStudents.as_view(), name='student'),
    path('students/', ViewAllStudents.as_view(), name='students'),

    path('getbatch/',CreateStudent.as_view(), name='getbatch'),
    path('createstudent/',CreateStudent.as_view(), name='createstudent'),
    path('editstudent/<int:id>/',CreateStudent.as_view(), name='editstudent'),
    path('deletestudent/<int:id>/', CreateStudent.as_view(), name='deletestudent'),

    path('createteacher/', CreateTeacher.as_view(), name='createteacher'),
    path('editteacher/<int:id>/', CreateTeacher.as_view(), name='editteacher'),
    path('deleteteacher/<int:id>/', CreateTeacher.as_view(), name='deleteteacher'),


]
