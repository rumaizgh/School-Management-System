from rest_framework.routers import DefaultRouter
from .views import AddSubject,ViewSubject,SubjectsByTeacher,DeleteSubject
from django.urls import path, include

router = DefaultRouter()

urlpatterns = [
    path('', ViewSubject.as_view(), name='viewsubject_root'),
    path('addsubject/', AddSubject.as_view(), name='addsubject'),
    path('viewsubject/', ViewSubject.as_view(), name='viewsubject'),
    path('viewsubject/<int:id>/', ViewSubject.as_view(), name='viewsubject_detail'),
    path('editsubject/<int:id>/', AddSubject.as_view(), name='editsubject'),
    path('teachersubject/<int:teacher_id>/', SubjectsByTeacher.as_view()),
    path('deletesubject/<int:id>/', DeleteSubject.as_view())
]