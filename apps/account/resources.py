from import_export import resources
from .models import UserData

class UserDataResource(resources.ModelResource):
    class Meta:
        model = UserData
        import_id_fields = ['email']
        skip_unchanged = True

    def skip_row(self, instance, original, row, import_validation_errors=None):
        email = row.get('email')
        if not email or str(email).strip() == '':
            return True
        return super().skip_row(instance, original, row, import_validation_errors)
