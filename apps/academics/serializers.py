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
    classs = serializers.StringRelatedField(source='teacher.classs', read_only=True, many=True)
    subject = serializers.StringRelatedField(source='teacher.subjects', many=True)
    class Meta:
        model = TimeTable
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
    