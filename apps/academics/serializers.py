from rest_framework import serializers
from .models import Batch,Fee,TimeTable,Payment

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = "__all__"

class FeeSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Payment
        fields = '__all__'
    
        
