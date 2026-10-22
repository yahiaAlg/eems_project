import re

from django.db import migrations

SUFFIX = re.compile(r"^([A-Za-z]+\d+)-\d+$")


def forwards(apps, schema_editor):
    Offering = apps.get_model("enrollment", "Offering")
    for o in Offering.objects.select_related("specialty").iterator():
        changed = []

        # 1) drop the "-{ORDER}" suffix: ELE0702-50 -> ELE0702
        base = None
        spec = o.specialty.code if o.specialty_id else ""
        if spec and o.code.startswith(spec + "-") and o.code[len(spec) + 1:].isdigit():
            base = spec
        else:
            m = SUFFIX.match(o.code)
            if m:
                base = m.group(1)
        if base and base != o.code:
            o.code = base
            changed.append("code")

        # 2) durations: days win; months only for exact multiples of 30
        days, months = o.duration_days, o.duration_months
        if days:
            new_months = days // 30 if days % 30 == 0 else None
            if new_months != months:
                o.duration_months = new_months
                changed.append("duration_months")
        elif months:
            o.duration_days = months * 30
            changed.append("duration_days")

        if changed:
            o.save(update_fields=changed)  # historical model: no custom save()


class Migration(migrations.Migration):
    dependencies = [("enrollment", "0027_offering_duration_help")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
