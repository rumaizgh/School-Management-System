from rest_framework.views import APIView
from .models import AttendanceSession, AttendanceRecord
from apps.subject.models import Subject
from .serializers import AttendanceSessionSerializer, AttendanceRecordSerializer, AttendanceRecordStudentSerializer
from rest_framework.response import Response
from apps.account.models import UserData
from apps.account.serializers import UserDataSerializer
from apps.subject.serializers import SubjectSerializer
from apps.academics.models import Batch
from apps.academics.serializers import BatchSerializer
from rest_framework.permissions import IsAuthenticated


class AttendanceSessionCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        serializer = AttendanceSessionSerializer(data=request.data)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
    
    def get(self, request, id=None):
        if not id:
            return Response({"error": "Teacher ID is required"}, status=400)
        
        teacher = UserData.objects.get(id=id, user_type='teacher')
        
        # Get subjects of this teacher
        subjects = Subject.objects.filter(teacher=teacher).values('id', 'subject_name')
        subjects_data = list(subjects)

        # Get batches of this teacher
        batches = Batch.objects.filter(subjects__teacher=teacher).values('id','classs').distinct()
        batches_data = list(batches)
        
        return Response({
            "subjects": subjects_data,
            "batches": batches_data
        })

class ViewAttendanceSessions(APIView):
    def get(self,request,id=None):
        if id:
            teacher = UserData.objects.get(id=id, user_type='teacher')
            records = AttendanceSession.objects.filter(teacher=teacher)
            serializer = AttendanceSessionSerializer(records, many=True)
            return Response(serializer.data)
        records = AttendanceSession.objects.all()
        serializer = AttendanceSessionSerializer(records, many=True)
        return Response(serializer.data)
    
class AttendanceStudentsList(APIView):
    def get(self,request,id):
        session = AttendanceSession.objects.get(id=id)
        classs = session.classs
        students = UserData.objects.filter(classs=classs, user_type='student')
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)

    def post(self,request):
        serializer = AttendanceRecordSerializer(data=request.data, many=True)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

class AttendanceRecordView(APIView):
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AttendanceRecordStudentSerializer
        return AttendanceRecordSerializer
    
    def get(self,request,id):
        session = AttendanceSession.objects.get(id=id)
        status = request.GET.get("status")
        record = AttendanceRecord.objects.filter(session=session)
        if status:
            record = record.filter(status=status)
        serializer = self.get_serializer_class()(record, many=True)
        return Response(serializer.data)
    
    def patch(self,request,id):
        record = AttendanceRecord.objects.get(id=id)
        serializer = self.get_serializer_class()(record, data = request.data, partial = True)
        if (serializer.is_valid()):
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)