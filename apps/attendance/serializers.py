from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord
from apps.account.models import UserData

class AttendanceSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    classs_name = serializers.CharField(source='classs.classs', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id','teacher', 'teacher_name', 'date', 'time', 'subject', 'subject_name', 'classs' , 'classs_name']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = '__all__'

class AttendanceRecordStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name', read_only=True)
    class Meta:
        model = AttendanceRecord
        fields = ['id','name','status']