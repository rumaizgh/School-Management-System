from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord

class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student', 'status']

class AttendanceSessionSerializer(serializers.ModelSerializer):
    records = AttendanceRecordSerializer(many=True)
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id', 'teacher', 'subject', 'date', 'records']

    def create(self, validated_data):
        records_data = validated_data.pop('records')
        session = AttendanceSession.objects.create(**validated_data)
        for record in records_data:
            AttendanceRecord.objects.create(session=session, **record)
        return session

