from rest_framework.routers import DefaultRouter
from .views import AddSubject,ViewSubject,SubjectsByTeacher
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('addsubject/', AddSubject.as_view(), name='addsubject'),
    path('viewsubject/', ViewSubject.as_view(), name='viewsubject'),
    path('viewsubject/<int:id>/', ViewSubject.as_view(), name='viewsubject'),
    path('editsubject/<int:id>/', AddSubject.as_view(), name='viewsubject'),
    path('teachersubject/<int:teacher_id>/', SubjectsByTeacher.as_view())


]