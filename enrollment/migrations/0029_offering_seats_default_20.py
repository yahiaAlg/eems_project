from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("enrollment", "0028_offering_code_and_duration_cleanup"),
    ]

    operations = [
        migrations.AlterField(
            model_name="offering",
            name="seats_available",
            field=models.PositiveSmallIntegerField(default=20, verbose_name="قدرة الاستيعاب"),
        ),
    ]
