from rest_framework import serializers
from .models import Batch,Fee

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