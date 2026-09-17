from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("enrollment", "0021_sessionchangerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="offering",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="تاريخ الإضافة"
            ),
        ),
        migrations.AddField(
            model_name="offering",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="آخر تعديل"
            ),
        ),
    ]
