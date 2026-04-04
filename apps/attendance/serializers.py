from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord
from apps.account.models import UserData

class AttendanceSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    batch_name = serializers.CharField(source='batch.batch', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id','teacher', 'teacher_name', 'date', 'time', 'subject', 'subject_name', 'batch' , 'batch_name']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = '__all__'

class AttendanceRecordStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name', read_only=True)
    session = serializers.CharField(source='session.teacher',read_only=True)
    class Meta:
        model = AttendanceRecord
        fields = ['id','name','status','session']

class ViewAttendanceRecordStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name', read_only=True)
    teacher = serializers.CharField(source='session.teacher', read_only=True)
    date = serializers.CharField(source='session.date', read_only=True)
    class Meta:
        model = AttendanceRecord
        fields = ['teacher','date','id','name','status']
