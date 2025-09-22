from rest_framework import serializers
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    subject_name = serializers.CharField(source="subject.subject_name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.name", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id',
            'student', 'student_name',
            'subject', 'subject_name',
            'teacher', 'teacher_name',
            'date', 'status', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['teacher', 'created_at', 'updated_at']
