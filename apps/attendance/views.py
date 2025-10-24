from rest_framework.response import Response
from django.shortcuts import redirect
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

class AtdSession(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        teacher = request.user

        subjects_fk = Subject.objects.filter(teacher=teacher)
        
        subjects_m2m = teacher.subject.all()
        
        all_subjects = (subjects_fk | subjects_m2m).distinct()
        
        all_subjects = all_subjects.select_related('classs')
        
        subject_data = [
            {
                "id": s.id,
                "subject_name": s.subject_name,
                "subject_code": s.subject_code,
                "batch": {
                    "id": s.classs.id,
                    "class": s.classs.classs,
                    "year": s.classs.year,
                    "batch": s.classs.batch,
                    "display": str(s.classs)
                } if s.classs else None
            }
            for s in all_subjects
        ]

        return Response({
            "teacher_id": teacher.id,
            "teacher_name": teacher.name,
            "subjects": subject_data
        })