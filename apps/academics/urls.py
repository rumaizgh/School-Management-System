from rest_framework.routers import DefaultRouter
from .views import CreateClass
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('class/', CreateClass.as_view()),
    path('class/<int:id>/', CreateClass.as_view()),
]
