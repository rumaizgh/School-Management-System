from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/subject/', include('apps.subject.urls')),
    path('api/account/', include('apps.account.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/batch/', include('apps.academics.urls')),
    path('api/academics/', include('apps.academics.urls')),
    path('api/fee/', include('apps.academics.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/payroll/', include('apps.payroll.urls')),
    path('api/reports/', include('apps.reports.urls')),

    # Web Admin Portal
    path('dashboard/', include('apps.web_admin.urls')),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
