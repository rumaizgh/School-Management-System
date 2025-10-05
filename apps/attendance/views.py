from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import AttendanceSession
from .serializers import AttendanceSessionSerializer, AttendanceRecordSerializer
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