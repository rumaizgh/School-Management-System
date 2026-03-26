from rest_framework.routers import DefaultRouter
from .views import CreateClass,ViewAllClassTeacher,ViewStudentsByClass,ViewTeachersByClass
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('class/teacher/', ViewAllClassTeacher.as_view()),
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
    path('class/students/<int:id>/', ViewStudentsByClass.as_view()),
    path('class/teachers/<int:id>/', ViewTeachersByClass.as_view())
]
