from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Subject
from .serializers import SubjectSerializer
from .permissions import IsAdmin
from django.shortcuts import get_object_or_404

class ViewSubject(APIView):
    def get(self,request,id=None):
        if id:
            subject = get_object_or_404(Subject,id=id)
            serializer = SubjectSerializer(subject)
            return Response(serializer.data)
        subject = Subject.objects.all()
        serializer = SubjectSerializer(subject,many=True)
        return Response(serializer.data)

class AddSubject(APIView):
    def post(self,request):
        serializer = SubjectSerializer(data = request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors)
    
    def patch(self, request, id):
        timetable=get_object_or_404(Subject,id=id)
        serializer = SubjectSerializer(timetable, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SubjectsByTeacher(APIView):
    def get(self, request, teacher_id):
        subjects = Subject.objects.filter(teacher_id=teacher_id)

        if not subjects.exists():
            return Response(
                {"message": "No subjects found for this teacher"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)