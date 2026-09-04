from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Subject, Chapter, Topic
from .serializers import SubjectSerializer, ChapterSerializer, TopicSerializer
from .permissions import IsAdmin
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend
from apps.account.models import UserData
from apps.notifications.services import send_chapter_completion_notification


class ViewSubject(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        if id:
            subject = get_institute_scoped_object_or_404(Subject, request, id=id)
            serializer = SubjectSerializer(subject)
            return Response(serializer.data)

        user = request.user
        subjects = InstituteFilterBackend().filter_queryset(request, Subject.objects.all(), None)

        if user.user_type == 'teacher':
            subjects = subjects.filter(teacher=user)

        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)


class AddSubject(APIView):
    def post(self, request):
        serializer = SubjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(institute=request.user.institute)
            return Response(serializer.data, status=201)
        return Response(serializer.errors)

    def patch(self, request, id):
        timetable = get_institute_scoped_object_or_404(Subject, request, id=id)
        serializer = SubjectSerializer(timetable, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubjectsByTeacher(APIView):
    def get(self, request, teacher_id):
        subjects = Subject.objects.filter(teacher_id=teacher_id)
        subjects = InstituteFilterBackend().filter_queryset(request, subjects, None)

        if not subjects.exists():
            return Response(
                {"message": "No subjects found for this teacher"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteSubject(APIView):
    def delete(self, request, id):
        subject = get_institute_scoped_object_or_404(Subject, request, id=id)
        subject.delete()
        return Response(
            {"message": "Subject deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


class ViewSubjectSyllabusProgress(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        chapters = subject.chapters.all().prefetch_related('topics')

        today = timezone.localdate()
        total_chapters = chapters.count()
        completed_chapters = chapters.filter(status='completed').count()
        in_progress_chapters = chapters.filter(status='in_progress').count()
        pending_chapters = chapters.filter(status='not_started').count()
        overdue_chapters = chapters.exclude(status='completed').filter(target_date__lt=today).count()

        if total_chapters > 0:
            overall_completion_percentage = round((completed_chapters / total_chapters) * 100, 2)
        else:
            overall_completion_percentage = 0.0

        chapter_serializer = ChapterSerializer(chapters, many=True)

        return Response({
            "subject_id": subject.id,
            "subject_name": subject.subject_name,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "in_progress_chapters": in_progress_chapters,
            "pending_chapters": pending_chapters,
            "overdue_chapters": overdue_chapters,
            "overall_completion_percentage": overall_completion_percentage,
            "chapters": chapter_serializer.data
        }, status=status.HTTP_200_OK)


class ViewTeacherSyllabusProgress(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        teacher = get_object_or_404(UserData, id=teacher_id, user_type='teacher')
        subjects = Subject.objects.filter(teacher=teacher).prefetch_related('chapters')

        subjects_data = []
        for subject in subjects:
            total_chapters = subject.chapters.count()
            completed_chapters = subject.chapters.filter(status='completed').count()
            if total_chapters > 0:
                overall_percentage = round((completed_chapters / total_chapters) * 100, 2)
            else:
                overall_percentage = 0.0

            class_name = str(subject.classs) if subject.classs else "N/A"

            subjects_data.append({
                "subject_id": subject.id,
                "subject_name": subject.subject_name,
                "class_name": class_name,
                "total_chapters": total_chapters,
                "completed_chapters": completed_chapters,
                "overall_completion_percentage": overall_percentage
            })

        return Response({
            "teacher_id": teacher.id,
            "teacher_name": teacher.name or "Teacher",
            "subjects": subjects_data
        }, status=status.HTTP_200_OK)


class ViewStudentClassSubjects(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        batch = user.classs.first() if hasattr(user, 'classs') else None
        if not batch:
            return Response({
                "message": "Student is not enrolled in any active class."
            }, status=status.HTTP_404_NOT_FOUND)

        subjects = batch.subjects.all().prefetch_related('chapters', 'teacher')
        subjects_data = []

        for subject in subjects:
            total_chapters = subject.chapters.count()
            completed_chapters = subject.chapters.filter(status='completed').count()
            if total_chapters > 0:
                overall_percentage = round((completed_chapters / total_chapters) * 100, 2)
            else:
                overall_percentage = 0.0

            teacher_id = subject.teacher.id if subject.teacher else None
            teacher_name = subject.teacher.name if subject.teacher else None

            subjects_data.append({
                "id": subject.id,
                "subject_name": subject.subject_name,
                "subject_code": subject.subject_code,
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "overall_completion_percentage": overall_percentage
            })

        return Response({
            "class_id": batch.id,
            "class_name": str(batch),
            "total_subjects": len(subjects_data),
            "subjects": subjects_data
        }, status=status.HTTP_200_OK)


class SyllabusChapterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChapterSerializer(data=request.data)
        if serializer.is_valid():
            chapter = serializer.save()
            return Response(ChapterSerializer(chapter).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SyllabusChapterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        old_status = chapter.status

        serializer = ChapterSerializer(chapter, data=request.data, partial=True)
        if serializer.is_valid():
            updated_chapter = serializer.save()

            # Trigger Task B notification if status transitions to completed
            if updated_chapter.notify_students_on_completion:
                is_now_completed = (
                    updated_chapter.status == 'completed' or
                    updated_chapter.completion_percentage == 100.0
                )
                was_completed = (old_status == 'completed')
                if is_now_completed and not was_completed:
                    send_chapter_completion_notification(updated_chapter)

            return Response(ChapterSerializer(updated_chapter).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        chapter.delete()
        return Response(
            {"message": "Chapter deleted successfully"},
            status=status.HTTP_200_OK
        )