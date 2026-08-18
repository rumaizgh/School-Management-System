from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Subject
from .serializers import SubjectSerializer
from .permissions import IsAdmin
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend

class ViewSubject(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request,id=None):
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
    def post(self,request):
        serializer = SubjectSerializer(data = request.data)
        if (serializer.is_valid()):
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