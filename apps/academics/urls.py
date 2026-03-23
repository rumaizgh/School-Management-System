from rest_framework.routers import DefaultRouter
from .views import CreateClass,ViewAllClassTeacher
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('class/teacher/', ViewAllClassTeacher.as_view()),
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
]
