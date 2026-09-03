from rest_framework import serializers
from django.utils import timezone
from apps.account.models import UserData
from .models import TeacherSalary, SalaryPayment


# ---------------------------------------------------------------------------
# Salary Config Serializers
# ---------------------------------------------------------------------------

class SalaryConfigCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/payroll/teachers/{id}/salary-config/
    Accepts both hourly and monthly payloads.
    """

    class Meta:
        model = TeacherSalary
        fields = [
            'pay_type',
            'base_salary',
            'rate_per_unit',
            'units_completed',
            'allowances',
            'deductions',
            'advance_deduction',
            'unpaid_leave_deduction',
            'pf_type',
            'pf_value',
            'tax_type',
            'tax_value',
            'month',
        ]
        extra_kwargs = {
            'base_salary': {'required': False},
            'rate_per_unit': {'required': False},
            'units_completed': {'required': False, 'allow_null': True},
            'allowances': {'required': False},
            'deductions': {'required': False},
            'advance_deduction': {'required': False},
            'unpaid_leave_deduction': {'required': False},
        }

    def validate_month(self, value):
        """Enforce YYYY-MM format."""
        import re
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', value):
            raise serializers.ValidationError("month must be in YYYY-MM format (e.g. 2026-08).")
        return value

    def validate(self, data):
        pay_type = data.get('pay_type', 'monthly')
        if pay_type == 'hourly' and not data.get('rate_per_unit'):
            raise serializers.ValidationError({'rate_per_unit': 'rate_per_unit is required for hourly pay type.'})
        if pay_type == 'monthly' and not data.get('base_salary'):
            raise serializers.ValidationError({'base_salary': 'base_salary is required for monthly pay type.'})
        return data


class SalaryDetailSerializer(serializers.ModelSerializer):
    """
    Used for GET — returns full computed payroll breakdown.
    All computed fields are read-only and calculated at serialization time.
    """
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    gross_salary = serializers.SerializerMethodField()
    pf_deduction = serializers.SerializerMethodField()
    tax_deduction = serializers.SerializerMethodField()
    net_salary = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = TeacherSalary
        fields = [
            'id',
            'teacher_id',
            'teacher_name',
            'month',
            'status',
            'pay_type',
            'base_salary',
            'rate_per_unit',
            'units_completed',
            'gross_salary',
            'allowances',
            'deductions',
            'advance_deduction',
            'unpaid_leave_deduction',
            'tax_deduction',
            'pf_deduction',
            'net_salary',
            'total_paid',
            'balance',
            'payment_status',
        ]

    def get_gross_salary(self, obj):
        return obj.gross_salary

    def get_pf_deduction(self, obj):
        return obj.pf_deduction

    def get_tax_deduction(self, obj):
        return obj.tax_deduction

    def get_net_salary(self, obj):
        return obj.net_salary

    def get_total_paid(self, obj):
        return obj.total_paid

    def get_balance(self, obj):
        return obj.balance

    def get_payment_status(self, obj):
        return obj.payment_status


# ---------------------------------------------------------------------------
# Salary Payment Serializers
# ---------------------------------------------------------------------------

class SalaryPaymentSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/payroll/disburse/ and GET history endpoints.
    Accepts and returns 'salary_id' and 'teacher_id' as specified in the API documentation.
    """
    salary_id = serializers.PrimaryKeyRelatedField(
        queryset=TeacherSalary.objects.all(),
        source='salary'
    )
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=UserData.objects.filter(user_type='teacher'),
        source='teacher'
    )
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    month = serializers.CharField(source='salary.month', read_only=True)

    class Meta:
        model = SalaryPayment
        fields = [
            'id',
            'salary_id',
            'teacher_id',
            'teacher_name',
            'month',
            'amount',
            'payment_method',
            'transaction_id',
            'paid_on',
            'remarks',
        ]
        extra_kwargs = {
            'transaction_id': {'required': False, 'allow_null': True, 'allow_blank': True},
            'remarks': {'required': False, 'allow_null': True, 'allow_blank': True},
            'paid_on': {'required': False},
        }

    def validate(self, data):
        salary = data.get('salary')
        teacher = data.get('teacher')
        amount = data.get('amount')

        if salary and teacher and salary.teacher_id != teacher.id:
            raise serializers.ValidationError(
                {'teacher_id': 'teacher_id does not match the salary record\'s teacher.'}
            )

        if salary and amount is not None:
            if amount <= 0:
                raise serializers.ValidationError({'amount': 'Amount must be greater than zero.'})
            if float(amount) > salary.balance:
                raise serializers.ValidationError(
                    {'amount': f'Amount ({amount}) exceeds outstanding balance ({salary.balance}).'}
                )

        return data

    def create(self, validated_data):
        if 'paid_on' not in validated_data or not validated_data['paid_on']:
            validated_data['paid_on'] = timezone.now()
        return super().create(validated_data)
