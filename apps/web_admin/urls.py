from django.urls import path
from . import views

app_name = 'web_admin'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('', views.dashboard_view, name='dashboard'),
]
