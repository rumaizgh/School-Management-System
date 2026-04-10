from rest_framework import serializers
from .models import Batch,Fee,TimeTable,Payment
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
            subjects__classs=obj.id
        ).distinct().count()

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
    student_name = serializers.CharField(source='fee.student.name', read_only=True)
    classs_name = serializers.CharField(source='fee.batch.classs', read_only=True)
    balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'

    def get_total_paid(self, obj):
        total = Payment.objects.filter(
            fee=obj.fee,
            id__lte=obj.id
        ).aggregate(total=Sum('amount'))['total']
        return float(total or 0)

    def get_balance(self, obj):
        total_paid = self.get_total_paid(obj)
        return float(obj.fee.amount or 0) - total_paid