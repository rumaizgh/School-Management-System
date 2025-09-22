from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Attendance
from .serializers import AttendanceSerializer
from .permissions import IsTeacher

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        """
        Allow only teachers to create/update/delete.
        Students or others can read (GET).
        """
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAuthenticated, IsTeacher]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        Automatically assign the logged-in teacher as the subject's teacher.
        """
        serializer.save(teacher=self.request.user)