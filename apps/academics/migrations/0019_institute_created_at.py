from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0018_merge_20260903_0515'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE academics_institute ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
                    reverse_sql="ALTER TABLE academics_institute DROP COLUMN IF EXISTS created_at;"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='institute',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, null=True),
                ),
            ]
        ),
    ]

