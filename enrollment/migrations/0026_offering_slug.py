from django.db import migrations, models
from django.utils.text import slugify


def backfill_slugs(apps, schema_editor):
    Offering = apps.get_model("enrollment", "Offering")
    taken = {}
    for o in Offering.objects.order_by("pk"):
        if o.slug:
            taken.setdefault(o.session_id, set()).add(o.slug)
    for o in Offering.objects.filter(slug="").order_by("pk"):
        used = taken.setdefault(o.session_id, set())
        base = (slugify(o.title or "") or slugify(o.code or "") or "formation")[:160]
        slug, i = base, 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        Offering.objects.filter(pk=o.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ("enrollment", "0025_offering_daily_fee_offering_duration_days_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="offering",
            name="slug",
            field=models.SlugField(
                blank=True,
                db_index=True,
                help_text="يُولَّد تلقائياً من العنوان عند تركه فارغاً.",
                max_length=170,
                verbose_name="المعرف (slug)",
            ),
        ),
        migrations.RunPython(backfill_slugs, migrations.RunPython.noop),
    ]
