from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord
from apps.account.models import UserData

class AttendanceRecordSerializer(serializers.ModelSerializer):
    records = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )

    session = serializers.PrimaryKeyRelatedField(
        queryset=AttendanceSession.objects.all()
    )

    class Meta:
        model = AttendanceRecord
        fields = ['session', 'records']

    def validate(self, attrs):
        if not attrs.get('records'):
            raise serializers.ValidationError({"records": "This field cannot be empty."})
        return attrs

    def create(self, validated_data):
        session = validated_data['session']
        records_data = validated_data['records']
        created_records = []

        for record in records_data:
            student = record.get('student')
            status = record.get('status', 'absent')

            if not student:
                raise serializers.ValidationError({"student": "Each record must include a student ID."})

            obj, created = AttendanceRecord.objects.update_or_create(
                session=session,
                student_id=student,
                defaults={'status': status}
            )
            created_records.append(obj)

        return created_records

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
