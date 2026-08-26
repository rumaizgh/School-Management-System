from rest_framework import serializers
from .models import Batch,Fee,TimeTable,Payment,Mark,Institute,Exam
from apps.account.models import UserData
from django.db.models import Count, Q, Sum

class InstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institute
        fields = '__all__'

class BatchSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    total_fee = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    percentage_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = '__all__'

    def get_students(self, obj):
        return UserData.objects.filter(
            user_type='student',
            is_active=True,
            classs=obj.id
        ).count()
    
    def get_teachers(self, obj):
        return UserData.objects.filter(
            user_type='teacher',
            is_active=True,
            classs=obj.id
        ).count()

    def get_total_fee(self, obj):
        return Fee.objects.filter(
            batch=obj.id
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_total_paid(self, obj):
        return Payment.objects.filter(
            fee__batch=obj.id
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    def get_balance(self, obj):
        total_fee = self.get_total_fee(obj)
        total_paid = self.get_total_paid(obj)
        return total_fee - total_paid

    def get_percentage_paid(self, obj):
        total_fee = self.get_total_fee(obj)
        total_paid = self.get_total_paid(obj)

        if total_fee > 0:
            return round((total_paid / total_fee) * 100, 2)
        return 0

class FeeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = '__all__'  

    def get_balance(self, obj):
        return obj.balance()

    def get_total_paid(self, obj):
        return obj.total_paid()
    
class TimeTableSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    classs_name = serializers.CharField(source='classs.classs', read_only=True)
    session = serializers.SerializerMethodField()

    class Meta:
        model = TimeTable
        fields = [
            'id',
            'teacher', 'teacher_name',
            'subject', 'subject_name',
            'classs', 'classs_name',
            'date',
            'day',
            'start_time',
            'end_time',
            'is_exam',
            'session',
        ]

    def get_session(self, obj):
        sessions = list(obj.sessions.all())
        if sessions:
            return sessions[0].id
        from apps.attendance.models import AttendanceSession
        session_obj = AttendanceSession.objects.filter(
            teacher=obj.teacher,
            classs=obj.classs,
            date=obj.date,
            time=obj.start_time
        ).first()
        return session_obj.id if session_obj else None

class PaymentSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    classs_name = serializers.CharField(source='fee.batch.classs', read_only=True)
    balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'fee', 'amount', 'payment_method', 'paid_on', 'student', 'classs_name', 'balance', 'total_paid']

    def get_total_paid(self, obj):
        total = Payment.objects.filter(
            fee=obj.fee,
            id__lte=obj.id
        ).aggregate(total=Sum('amount'))['total']
        return float(total or 0)

    def get_balance(self, obj):
        total_paid = self.get_total_paid(obj)
        return float(obj.fee.amount or 0) - total_paid
    
    def get_student(self, obj):
        return {
            "id": obj.fee.student.id,
            "name": obj.fee.student.name,
            "phone": obj.fee.student.phone,
            "parent_contact": obj.fee.student.parent_contact
        }


class MarkSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.exam_name', read_only=True)
    total_mark = serializers.DecimalField(source='exam.total_mark', max_digits=10, decimal_places=2, read_only=True)
    subject = serializers.PrimaryKeyRelatedField(source='exam.subject', read_only=True)
    subject_name = serializers.CharField(source='exam.subject.subject_name', read_only=True)
    batch = serializers.PrimaryKeyRelatedField(source='exam.batch', read_only=True)
    batch_name = serializers.CharField(source='exam.batch.classs', read_only=True)
    student_name = serializers.CharField(source='student.name', read_only=True)
    
    class Meta:
        model = Mark
        fields = ['id', 'exam', 'exam_name', 'subject', 'subject_name', 'student', 'student_name', 'batch', 'batch_name', 'total_mark', 'obtained_mark', 'percentage']
        read_only_fields = ['id', 'subject', 'subject_name', 'batch', 'batch_name', 'total_mark', 'percentage']

    def validate(self, data):
        exam = data.get('exam') if data.get('exam') is not None else (self.instance.exam if getattr(self, 'instance', None) else None)
        student = data.get('student') if data.get('student') is not None else (self.instance.student if getattr(self, 'instance', None) else None)

        # Validate obtained_mark does not exceed exam's total_mark
        total = exam.total_mark if (exam and exam.total_mark is not None) else None
        obtained = data.get('obtained_mark') if data.get('obtained_mark') is not None else (self.instance.obtained_mark if getattr(self, 'instance', None) else None)
        if total is not None and obtained is not None:
            if obtained > total:
                raise serializers.ValidationError({'obtained_mark': f'obtained_mark cannot be greater than total_mark ({total}).'})

        # Ensure the student belongs to the exam's batch
        if exam and exam.batch and student:
            if not student.classs.filter(id=exam.batch.id).exists():
                raise serializers.ValidationError({'student': 'Student does not belong to the batch of the selected exam.'})

        # Validate that each student can only have one mark per exam
        if student and exam:
            existing_mark = Mark.objects.filter(exam=exam, student=student)
            if self.instance:
                existing_mark = existing_mark.exclude(id=self.instance.id)
            if existing_mark.exists():
                raise serializers.ValidationError({'exam': 'This student already has a mark for this exam.'})

        return data

class ExamSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.classs', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    session = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'exam_name', 'batch', 'batch_name', 'subject', 'subject_name', 'timetable', 'session', 'total_mark', 'pass_mark', 'question_paper']

    def get_session(self, obj):
        if not obj.timetable:
            return None
        sessions = list(obj.timetable.sessions.all())
        if sessions:
            return sessions[0].id
        from apps.attendance.models import AttendanceSession
        session_obj = AttendanceSession.objects.filter(
            teacher=obj.timetable.teacher,
            classs=obj.timetable.classs,
            date=obj.timetable.date,
            time=obj.timetable.start_time
        ).first()
        return session_obj.id if session_obj else None

    def validate(self, data):
        total = data.get('total_mark') if data.get('total_mark') is not None else (self.instance.total_mark if getattr(self, 'instance', None) else None)
        pass_mark = data.get('pass_mark') if data.get('pass_mark') is not None else (self.instance.pass_mark if getattr(self, 'instance', None) else None)
        if pass_mark is not None:
            if pass_mark < 0:
                raise serializers.ValidationError({'pass_mark': 'pass_mark cannot be negative.'})
            if total is not None and pass_mark > total:
                raise serializers.ValidationError({'pass_mark': 'pass_mark cannot be greater than total_mark.'})

        timetable = data.get('timetable') if 'timetable' in data else (self.instance.timetable if getattr(self, 'instance', None) else None)
        if timetable:
            qs = Exam.objects.filter(timetable=timetable, is_deleted=False)
            if getattr(self, 'instance', None) and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'timetable': 'This timetable is already assigned to another exam.'})

            batch = data.get('batch') if 'batch' in data else (self.instance.batch if getattr(self, 'instance', None) else None)
            if batch and timetable.classs != batch:
                raise serializers.ValidationError({'timetable': 'Selected timetable class does not match the exam batch.'})

        return data

class ExamAnalyticsSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField()
    total_students_attended = serializers.IntegerField()
    highest_mark = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    top_scorer_name = serializers.CharField(allow_null=True)
    lowest_mark = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    average_mark = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    pass_mark = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    pass_percentage = serializers.FloatField()

class BulkMarkItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    obtained_mark = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False)

class BulkMarkSerializer(serializers.Serializer):
    marks = BulkMarkItemSerializer(many=True)