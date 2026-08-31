from import_export import resources, fields
from .models import UserData

class UserDataResource(resources.ModelResource):
    classes = fields.Field(column_name='Class/Batch')
    subjects = fields.Field(column_name='Subjects')
    institute_name = fields.Field(column_name='Institute')

    class Meta:
        model = UserData
        import_id_fields = ['email']
        skip_unchanged = True
        fields = (
            'id', 'roll_number', 'name', 'email', 'gender', 'user_type', 'phone', 'address',
            'date_of_birth', 'parent_name', 'parent_contact',
            'classes', 'subjects', 'institute_name'
        )
        export_order = fields

    def skip_row(self, instance, original, row, import_validation_errors=None):
        email = row.get('email')
        if not email or str(email).strip() == '':
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    def dehydrate_classes(self, obj):
        return ", ".join([str(b) for b in obj.classs.all()])

    def dehydrate_subjects(self, obj):
        return ", ".join([getattr(s, 'subject_name', str(s)) for s in obj.subject.all()])

    def dehydrate_institute_name(self, obj):
        return obj.institute.name if obj.institute else ""


