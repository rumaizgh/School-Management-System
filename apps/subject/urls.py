from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    AddSubject,
    ViewSubject,
    SubjectsByTeacher,
    DeleteSubject,
    ViewSubjectSyllabusProgress,
    ViewTeacherSyllabusProgress,
    ViewStudentClassSubjects,
    SyllabusChapterView,
    SyllabusChapterDetailView,
)

router = DefaultRouter()

urlpatterns = [
    path('', ViewSubject.as_view(), name='viewsubject_root'),
    path('addsubject/', AddSubject.as_view(), name='addsubject'),
    path('viewsubject/', ViewSubject.as_view(), name='viewsubject'),
    path('viewsubject/<int:id>/', ViewSubject.as_view(), name='viewsubject_detail'),
    path('editsubject/<int:id>/', AddSubject.as_view(), name='editsubject'),
    path('teachersubject/<int:teacher_id>/', SubjectsByTeacher.as_view()),
    path('deletesubject/<int:id>/', DeleteSubject.as_view()),

    # Subject Syllabus & Progress Tracking APIs
    path('syllabus/<int:subject_id>/', ViewSubjectSyllabusProgress.as_view(), name='subject_syllabus_progress'),
    path('syllabus/teacher/<int:teacher_id>/', ViewTeacherSyllabusProgress.as_view(), name='teacher_syllabus_progress'),
    path('student/me/', ViewStudentClassSubjects.as_view(), name='student_class_subjects'),
    path('syllabus/', SyllabusChapterView.as_view(), name='create_syllabus_chapter'),
    path('syllabus/chapter/<int:chapter_id>/', SyllabusChapterDetailView.as_view(), name='syllabus_chapter_detail'),
]