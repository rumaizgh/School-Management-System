from rest_framework import serializers
from .models import Batch,Fee,TimeTable

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = "__all__"

class FeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fee
        fields = ['id', 'student', 'amount', 'due_date', 'batch', 'paid_amount','balance_amount', 'paid', 'paid_on']
        read_only_fields = ['batch', 'paid', 'paid_on','balance_amount']

    def create(self, validated_data):
        student = validated_data['student']
        validated_data['batch'] = student.batch
        fee = Fee(**validated_data)
        fee.save()
        fee.refresh_from_db()
        return fee
    
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