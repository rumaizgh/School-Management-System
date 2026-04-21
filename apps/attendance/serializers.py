from rest_framework import serializers
from apps.academics.models import TimeTable
from .models import AttendanceSession, AttendanceRecord
from apps.account.models import UserData

class AttendanceSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    classs_name = serializers.CharField(source='classs.classs', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ['id', 'timetable', 'teacher', 'teacher_name', 'date', 'time',
                  'subject', 'subject_name', 'classs', 'classs_name']
        read_only_fields = ['teacher', 'subject', 'classs', 'date', 'time']

    def validate_timetable(self, value):
        if AttendanceSession.objects.filter(timetable=value).exists():
            raise serializers.ValidationError(
                "An attendance session already exists for this timetable."
            )
        return value

    def create(self, validated_data):
        timetable = validated_data['timetable']
        validated_data['teacher'] = timetable.teacher
        validated_data['subject'] = timetable.subject
        validated_data['classs'] = timetable.classs
        validated_data['date'] = timetable.date
        validated_data['time'] = timetable.start_time
        return super().create(validated_data)
     
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
    subject = serializers.SerializerMethodField()
    time = serializers.CharField(source='session.time', read_only = True)

    class Meta:
        model = AttendanceRecord
        fields = ['teacher', 'subject', 'date','time', 'id', 'name', 'status']

    def get_subject(self, obj):
        session = obj.session
        day = session.date.strftime('%a').lower()[:3]

        timetable = TimeTable.objects.filter(
            classs=session.classs,
            day=day,
            start_time=session.time
        ).first()

        if timetable:
            return timetable.subject.subject_name

        if session.subject:
            return session.subject.subject_name

        return None