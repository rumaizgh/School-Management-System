from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserDataViewSet
from .views import LoginView


router = DefaultRouter()
router.register(r'users', UserDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api/login/', LoginView.as_view(), name='login'),
]
