from django.db import migrations, models
import django.db.models.deletion


DEFAULT_GRADES = (
    ('A+', 90, 100, 1),
    ('A', 80, 89.99, 2),
    ('B', 70, 79.99, 3),
    ('C', 60, 69.99, 4),
    ('D', 50, 59.99, 5),
    ('E', 0, 49.99, 6),
)


def create_default_grades(apps, schema_editor):
    Institute = apps.get_model('academics', 'Institute')
    Grade = apps.get_model('academics', 'Grade')
    Grade.objects.bulk_create([
        Grade(
            institute=institute,
            grade=grade,
            min_percentage=minimum,
            max_percentage=maximum,
            order=order,
        )
        for institute in Institute.objects.all()
        for grade, minimum, maximum, order in DEFAULT_GRADES
    ])


def remove_default_grades(apps, schema_editor):
    Grade = apps.get_model('academics', 'Grade')
    Grade.objects.filter(grade__in=[grade[0] for grade in DEFAULT_GRADES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0020_add_institute_domain_and_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='Grade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade', models.CharField(max_length=10)),
                ('min_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('max_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('order', models.PositiveIntegerField(default=0)),
                ('institute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='academics.institute')),
            ],
            options={
                'ordering': ['-min_percentage', 'order', 'id'],
                'constraints': [
                    models.UniqueConstraint(fields=('institute', 'grade'), name='unique_grade_per_institute'),
                    models.CheckConstraint(check=models.Q(('min_percentage__gte', 0), ('max_percentage__lte', 100)), name='grade_percentages_between_zero_and_hundred'),
                    models.CheckConstraint(check=models.Q(('min_percentage__lte', models.F('max_percentage'))), name='grade_min_percentage_lte_max_percentage'),
                ],
            },
        ),
        migrations.RunPython(create_default_grades, remove_default_grades),
    ]
