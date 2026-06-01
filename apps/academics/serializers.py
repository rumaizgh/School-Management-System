from rest_framework import serializers
from .models import Batch,Fee,TimeTable,Payment,Mark
from apps.account.models import UserData
from django.db.models import Count, Q, Sum

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
        ]

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
            "name": obj.fee.student.name
        }


class MarkSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField()
    student_name = serializers.CharField(source='student.name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    batch_name = serializers.CharField(source='batch.classs', read_only=True)
    
    class Meta:
        model = Mark
        fields = ['id', 'exam_name', 'subject', 'subject_name', 'student', 'student_name', 'batch', 'batch_name', 'total_mark', 'obtained_mark', 'percentage']
        read_only_fields = ['id', 'percentage']

    def validate(self, data):
        # Validate obtained_mark does not exceed total_mark
        total = data.get('total_mark') if data.get('total_mark') is not None else (self.instance.total_mark if getattr(self, 'instance', None) else None)
        obtained = data.get('obtained_mark') if data.get('obtained_mark') is not None else (self.instance.obtained_mark if getattr(self, 'instance', None) else None)
        if total is not None and obtained is not None:
            if obtained > total:
                raise serializers.ValidationError({'obtained_mark': 'obtained_mark cannot be greater than total_mark.'})

        # If batch provided, ensure the student belongs to that batch
        batch = data.get('batch')
        student = data.get('student') if data.get('student') is not None else (self.instance.student if getattr(self, 'instance', None) else None)
        if batch and student:
            # `classs` is a ManyToMany on UserData
            if not student.classs.filter(id=batch.id).exists():
                raise serializers.ValidationError({'student': 'Student does not belong to the selected batch.'})

        return data