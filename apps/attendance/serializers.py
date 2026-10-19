from rest_framework import serializers
from apps.academics.models import TimeTable
from .models import AttendanceSession, AttendanceRecord, StudentLeaveRequest
from apps.account.models import UserData

class AttendanceSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    classs_name = serializers.CharField(source='classs.classs', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            'id', 'timetable', 'teacher', 'teacher_name', 'date', 'time', 'end_time',
            'subject', 'subject_name', 'classs', 'classs_name', 'is_exam',
            'recorded_by', 'recorded_by_name', 'recorded_by_role', 'is_substitution',
            'created_at'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'teacher': {'required': False},
            'subject': {'required': False},
            'classs': {'required': False},
            'date': {'required': False},
            'time': {'required': False},
            'end_time': {'required': False},
            'is_exam': {'required': False},
            'recorded_by': {'required': False},
            'recorded_by_role': {'required': False},
            'is_substitution': {'required': False},
        }

    def create(self, validated_data):
        timetable = validated_data.get('timetable')
        if timetable:
            if not validated_data.get('teacher'):
                validated_data['teacher'] = timetable.teacher
            if not validated_data.get('subject'):
                validated_data['subject'] = timetable.subject
            if not validated_data.get('classs'):
                validated_data['classs'] = timetable.classs
            if not validated_data.get('date'):
                validated_data['date'] = timetable.date
            if not validated_data.get('time'):
                validated_data['time'] = timetable.start_time
            if not validated_data.get('end_time'):
                validated_data['end_time'] = timetable.end_time
            if 'is_exam' not in validated_data and hasattr(timetable, 'is_exam'):
                validated_data['is_exam'] = timetable.is_exam
        return super().create(validated_data)
     
class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = '__all__'

class AttendanceRecordStudentSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source='student.id', read_only=True, default=None)
    name = serializers.CharField(source='student.name', read_only=True, default=None)
    roll_no = serializers.CharField(source='student.roll_no', read_only=True, default=None)
    phone = serializers.CharField(source='student.phone', read_only=True, default=None)
    parent_contact = serializers.CharField(source='student.parent_contact', read_only=True, default=None)
    session = serializers.CharField(source='session.teacher', read_only=True)
    session_id = serializers.IntegerField(source='session.id', read_only=True, default=None)
    date = serializers.CharField(source='session.date', read_only=True, default=None)
    start_time = serializers.CharField(source='session.time', read_only=True, default=None)
    end_time = serializers.CharField(source='session.end_time', read_only=True, default=None)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            'id',
            'student_id',
            'name',
            'roll_no',
            'phone',
            'parent_contact',
            'status',
            'session',
            'session_id',
            'date',
            'start_time',
            'end_time',
            'profile',
            'leave_reason',
            'is_excused',
        ]

    def get_profile(self, obj):
        if obj.student and obj.student.profile:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.student.profile.url)
            return obj.student.profile.url
        return None

class ViewAttendanceRecordStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name', read_only=True)
    roll_no = serializers.CharField(source='student.roll_no', read_only=True)
    teacher = serializers.CharField(source='session.teacher', read_only=True)
    date = serializers.CharField(source='session.date', read_only=True)
    subject = serializers.SerializerMethodField()
    time = serializers.CharField(source='session.time', read_only = True)
    end_time = serializers.CharField(source='session.end_time', read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = ['teacher', 'subject', 'date', 'time', 'end_time', 'id', 'name', 'roll_no', 'status', 'profile', 'leave_reason', 'is_excused']

    def get_profile(self, obj):
        if obj.student and obj.student.profile:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.student.profile.url)
            return obj.student.profile.url
        return None

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


class StudentLeaveRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll = serializers.CharField(source='student.roll_no', read_only=True)
    class_name = serializers.SerializerMethodField(read_only=True)
    reviewed_by = serializers.SerializerMethodField(read_only=True)
    reviewed_by_id = serializers.IntegerField(source='reviewed_by.id', read_only=True, default=None)
    duration_days = serializers.FloatField(read_only=True)
    duration_label = serializers.CharField(read_only=True)
    formatted_date_range = serializers.CharField(read_only=True)

    class Meta:
        model = StudentLeaveRequest
        fields = [
            'id',
            'student',
            'student_name',
            'student_roll',
            'class_name',
            'start_date',
            'end_date',
            'is_half_day',
            'half_day_period',
            'reason_category',
            'reason_notes',
            'status',
            'admin_remarks',
            'reviewed_by',
            'reviewed_by_id',
            'reviewed_at',
            'duration_days',
            'duration_label',
            'formatted_date_range',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'admin_remarks',
            'reviewed_by',
            'reviewed_by_id',
            'reviewed_at',
            'duration_days',
            'duration_label',
            'formatted_date_range',
            'created_at',
            'updated_at',
        ]

    def get_class_name(self, obj):
        if obj.student:
            batch = obj.student.classs.first()
            if batch:
                return batch.classs
        return None

    def get_reviewed_by(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.name or obj.reviewed_by.email or "Principal Office"
        return None

    def validate(self, attrs):
        start_date = attrs.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date') or (self.instance.end_date if self.instance else None)
        is_half_day = attrs.get('is_half_day', self.instance.is_half_day if self.instance else False)
        half_day_period = attrs.get('half_day_period', self.instance.half_day_period if self.instance else None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})

        if is_half_day:
            if start_date and end_date and start_date != end_date:
                attrs['end_date'] = start_date
            if not half_day_period:
                raise serializers.ValidationError({"half_day_period": "half_day_period is required for half-day leave."})
            if half_day_period not in ['morning', 'afternoon']:
                raise serializers.ValidationError({"half_day_period": "half_day_period must be either 'morning' or 'afternoon'."})

        # Overlap check for student
        student = attrs.get('student') or (self.instance.student if self.instance else None)
        if student and start_date and end_date:
            target_end = attrs.get('end_date', end_date)
            overlap_qs = StudentLeaveRequest.objects.filter(
                student=student,
                status__in=['pending', 'approved'],
                start_date__lte=target_end,
                end_date__gte=start_date
            )
            if self.instance:
                overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
            if overlap_qs.exists():
                raise serializers.ValidationError({
                    "non_field_errors": ["There is already a leave request on that date range."]
                })

        return attrs