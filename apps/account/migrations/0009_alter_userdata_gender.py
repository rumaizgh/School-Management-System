# Generated manually for changing gender field choices to plain CharField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_userdata_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdata',
            name='gender',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
