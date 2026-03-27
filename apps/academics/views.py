from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Batch, Fee
from .serializers import BatchSerializer
from apps.account.serializers import UserDataSerializer
from apps.academics.serializers import TimeTableSerializer
from .permissions import IsAdmin,IsTeacher
from django.shortcuts import get_object_or_404
from rest_framework import status
from apps.account.models import UserData
from apps.academics.models import TimeTable

class CreateClass(APIView):
    permission_classes=[IsAdmin]    
class TimeTablesView(APIView):
    def get(self, request):
        timetables = TimeTable.objects.all().order_by("day", "start_time")
        serializer = TimeTableSerializer(timetables, many=True)
        return Response(serializer.data)
    

    def post(self,request):
        serializer=BatchSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def get(self,request,id=None):
        if id:
            batch=get_object_or_404(Batch, id=id)
            serializer = BatchSerializer(batch)
            return Response(serializer.data)
        
        batches=Batch.objects.all()
        serializer=BatchSerializer(batches,many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        batch=get_object_or_404(Batch,id=id)
        serializer=BatchSerializer(batch,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def delete(self,request,id):
        batch = get_object_or_404(Batch,id=id)
        batch.delete()
        return Response({"message": "Batch deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class ViewAllClassTeacher(APIView):
    permission_classes=[IsTeacher]
    def get(self,request,id=None):
        teacher = request.user
        classs = Batch.objects.filter(subjects__teacher=teacher).distinct()
        serializer = BatchSerializer(classs,many=True)
        return Response(serializer.data)
    
class ViewStudentsByClass(APIView):
    def get(self, request, id):
        classs = get_object_or_404(Batch,id=id)
        students = UserData.objects.filter(classs=classs, user_type="student", is_active = True)
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)
    
class ViewTeachersByClass(APIView):
    def get(self, request, id):
        classs = get_object_or_404(Batch,id=id)
        teachers = UserData.objects.filter(classs=classs, user_type="teacher", is_active = True)
        serializer = UserDataSerializer(teachers, many=True)
        return Response(serializer.data)
     
class TimeTablesView(APIView):
    def get(self, request):
        timetables = TimeTable.objects.all().order_by("day", "start_time")
        serializer = TimeTableSerializer(timetables, many=True)
        return Response(serializer.data)
    
