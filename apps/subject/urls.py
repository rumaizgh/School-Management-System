from rest_framework.routers import DefaultRouter
from .views import AddSubject
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('addsubject/<int:id>/', AddSubject.as_view(), name='addsubject')
]