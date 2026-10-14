from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import InstitutionalTransaction


VALID_CATEGORIES = [
    'stationery',
    'utilities',
    'maintenance',
    'lab_supplies',
    'event',
    'canteen_rent',
    'donation',
    'fine',
    'miscellaneous',
]

VALID_PAYMENT_METHODS = ['cash', 'upi', 'bank_transfer', 'check']


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for creating, updating, and displaying Institutional Transactions.
    """
    id = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)
    date = serializers.DateTimeField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = InstitutionalTransaction
        fields = [
            'id',
            'type',
            'title',
            'amount',
            'category',
            'payment_method',
            'payment_reference',
            'reference_number',
            'remarks',
            'date',
            'is_edited',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_edited', 'created_at', 'updated_at']

    def get_id(self, obj):
        return f"tx-{obj.id}"

    def get_created_at(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        return None

    def get_updated_at(self, obj):
        if obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure date format is ISO UTC with Z
        if instance.date:
            ret['date'] = instance.date.strftime('%Y-%m-%dT%H:%M:%SZ')
        # Ensure amount is float for JSON
        if ret.get('amount') is not None:
            ret['amount'] = float(ret['amount'])
        return ret

    def validate_type(self, value):
        val = (value or '').strip().lower()
        if val not in ['expense', 'income']:
            raise serializers.ValidationError("Type must be 'expense' or 'income'.")
        return val

    def validate_amount(self, value):
        if value is None or value <= Decimal('0.00'):
            raise serializers.ValidationError("Enter a valid amount greater than 0.00")
        return value

    def validate_title(self, value):
        val = (value or '').strip()
        if len(val) < 2 or len(val) > 255:
            raise serializers.ValidationError("Title must be between 2 and 255 characters.")
        return val

    def validate_category(self, value):
        val = (value or '').strip().lower()
        if val not in VALID_CATEGORIES:
            raise serializers.ValidationError(
                f"Invalid category key '{value}'. Allowed categories: {VALID_CATEGORIES}."
            )
        return val

    def validate_payment_method(self, value):
        val = (value or '').strip().lower()
        if val == 'cheque':
            val = 'check'
        if val not in VALID_PAYMENT_METHODS:
            raise serializers.ValidationError(
                f"Payment method must be one of {VALID_PAYMENT_METHODS}."
            )
        return val


def format_validation_error_response(serializer_errors):
    """
    Formats DRF serializer errors into the specification's unified error payload:
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "<summary_message>",
      "errors": { ... }
    }
    """
    formatted_errors = {}
    for field, errs in serializer_errors.items():
        if isinstance(errs, list):
            formatted_errors[field] = [str(e) for e in errs]
        elif isinstance(errs, dict):
            formatted_errors[field] = [str(e) for e in errs.values()]
        else:
            formatted_errors[field] = [str(errs)]

    # Specific message for amount error as in specification
    if "amount" in formatted_errors:
        first_message = "Amount must be greater than zero."
    else:
        # Pick the first error message
        first_message = "Validation error."
        for field, err_list in formatted_errors.items():
            if err_list:
                first_message = err_list[0]
                break

    return {
        "status": "error",
        "code": "VALIDATION_ERROR",
        "message": first_message,
        "errors": formatted_errors,
    }
