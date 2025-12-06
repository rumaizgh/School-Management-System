from rest_framework.views import APIView
from .models import AttendanceSession, AttendanceRecord
from apps.subject.models import Subject
from .serializers import AttendanceSessionSerializer, AttendanceRecordSerializer
from rest_framework.response import Response
from apps.account.models import UserData
from apps.account.serializers import UserDataSerializer

class AttendanceSessionCreate(APIView):
    def get(self,request,id):
        atdSession = AttendanceSession.objects.get(id=id,teacher=request.user)
        serializer = AttendanceSessionSerializer(atdSession)
        return Response(serializer.data)

    def post(self,request):
        serializer = AttendanceSessionSerializer(data=request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
class AttendanceStudentsList(APIView):
    def get(self,request,id):
        session = AttendanceSession.objects.get(id=id)
        batch = session.batch
        students = UserData.objects.filter(batch=batch, user_type='student')
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)

    def post(self,request,id):
        serializer = AttendanceRecordSerializer(data=request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

class AttendanceRecordView(APIView):
    def get(self,request,id):
        session = AttendanceSession.objects.get(id=id)
        record = AttendanceRecord.objects.filter(session=session)
        serializer = AttendanceRecordSerializer(record, many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        record = AttendanceRecord.objects.get(id=id)
        serializer = AttendanceRecordSerializer(record, data = request.data, partial = True)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)