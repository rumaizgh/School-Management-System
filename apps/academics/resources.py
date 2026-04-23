from import_export import resources
from .models import Fee
from import_export import resources, fields
from apps.account.models import UserData

class FeeResource(resources.ModelResource):

    total_paid = fields.Field()
    balance = fields.Field()

    class Meta:
        model = Fee
        fields = ('student__name', 'amount', 'total_paid', 'balance')

    def dehydrate_total_paid(self, obj):
        return obj.total_paid()

    def dehydrate_balance(self, obj):
        return obj.balance()
    
class UserDataResource(resources.ModelResource):
    class Meta:
        model = UserData
        skip_unchanged = True
        import_id_fields = ['email']

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not row.get('email'):
            return True  # silently skip blank rows
        return super().skip_row(instance, original, row, import_validation_errors)