from rest_framework.routers import DefaultRouter
from .views import BatchViewSet, FeeViewSet

router = DefaultRouter()
router.register(r'batch', BatchViewSet, basename='batch')
router.register(r'fee', FeeViewSet, basename='fee')
urlpatterns = router.urls
