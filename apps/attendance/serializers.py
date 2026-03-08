from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord
from apps.account.models import UserData

class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = '__all__'

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = '__all__'

class AttendanceRecordStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name', read_only=True)
    class Meta:
        model = AttendanceRecord
        fields = ['name','status']