from import_export import resources
from .models import Fee
from import_export import resources, fields
from apps.account.models import UserData

class FeeResource(resources.ModelResource):

    batch_name = fields.Field(column_name='Batch Name')
    total_paid = fields.Field(column_name='Total Paid')
    balance = fields.Field(column_name='Balance')

    class Meta:
        model = Fee
        fields = ('student__name', 'batch_name', 'amount', 'total_paid', 'balance')

    def dehydrate_batch_name(self, obj):
        return str(obj.batch)

    def dehydrate_total_paid(self, obj):
        return obj.total_paid()

    def dehydrate_balance(self, obj):
        return obj.balance()
    