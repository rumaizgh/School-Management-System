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
    