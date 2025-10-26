from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from apps.subject.models import Subject
from .models import AttendanceSession
from .serializers import AttendanceSessionSerializer
from .permissions import IsTeacher
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import AttendanceSession
from .serializers import AttendanceSessionSerializer

class AttendanceSessionViewSet(viewsets.ModelViewSet):
    queryset = AttendanceSession.objects.all()
    serializer_class = AttendanceSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAuthenticated, IsTeacher]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.subject.models import Subject

from apps.academics.models import Batch

class AtdSession(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        teacher = request.user

        batch_id = request.data.get("batch_id")
        subject_id = request.data.get("subject_id")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")

        time = f"{start_time} - {end_time}"

        if not batch_id or not subject_id or not time:
            return Response({"error": "Missing batch_id, subject_id, or time"}, status=400)

        batch = get_object_or_404(Batch, id=batch_id)
        subject = get_object_or_404(Subject, id=subject_id)

        attendance = AttendanceSession.objects.create(
            teacher=teacher,
            batch=batch,
            subject=subject,
            time=time
        )

        return Response({
            "message": "Attendance session created successfully",
            "session_id": attendance.id,
            "teacher": teacher.name,
            "batch": str(batch),
            "subject": subject.subject_name,
            "time": time
        }, status=201)

    def list(self, request):
        teacher = request.user

        subjects_m2m = teacher.subject.all()

        all_batches = Batch.objects.all()
        
        batch_data = [
            {
                "id": b.id,
                "class": b.classs,
                "batch": b.batch,
                "display": str(b)
            }
            for b in all_batches
        ]
        
        subject_data = [
            {
                "id": s.id,
                "subject_name": s.subject_name,
                "subject_code": s.subject_code,
            }
            for s in subjects_m2m
        ]

        return Response({
            "teacher_id": teacher.id,
            "teacher_name": teacher.name,
            "subjects": subject_data,
            "batches": batch_data
        })