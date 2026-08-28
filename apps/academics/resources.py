from import_export import resources, fields
from .models import Fee, Mark
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


class MarkResource(resources.ModelResource):
    student_name = fields.Field(column_name='Student Name')
    student_email = fields.Field(column_name='Student Email')
    student_roll_no = fields.Field(column_name='Roll No')
    exam_name = fields.Field(column_name='Exam Name')
    subject_name = fields.Field(column_name='Subject')
    batch_name = fields.Field(column_name='Batch Name')
    total_mark = fields.Field(column_name='Total Mark')
    obtained_mark = fields.Field(column_name='Obtained Mark')
    percentage = fields.Field(column_name='Percentage (%)')

    class Meta:
        model = Mark
        fields = (
            'id', 'student_roll_no', 'student_name', 'student_email',
            'batch_name', 'exam_name', 'subject_name', 'total_mark',
            'obtained_mark', 'percentage'
        )
        export_order = fields

    def dehydrate_student_name(self, obj):
        return obj.student.name if obj.student else ""

    def dehydrate_student_email(self, obj):
        return obj.student.email if obj.student else ""

    def dehydrate_student_roll_no(self, obj):
        return obj.student.roll_no if obj.student else ""

    def dehydrate_exam_name(self, obj):
        return obj.exam.exam_name if obj.exam else ""

    def dehydrate_subject_name(self, obj):
        return str(obj.exam.subject) if (obj.exam and obj.exam.subject) else ""

    def dehydrate_batch_name(self, obj):
        return str(obj.exam.batch) if (obj.exam and obj.exam.batch) else ""

    def dehydrate_total_mark(self, obj):
        return obj.exam.total_mark if (obj.exam and obj.exam.total_mark) else ""

    def dehydrate_obtained_mark(self, obj):
        return obj.obtained_mark

    def dehydrate_percentage(self, obj):
        return obj.percentage

    