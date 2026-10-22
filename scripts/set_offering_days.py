"""
Set every Offering (training) to a fixed number of training days.

Usage (from the project folder):
    python manage.py shell < scripts/set_offering_days.py                 # DRY-RUN
    APPLY=1 python manage.py shell < scripts/set_offering_days.py         # writes
    DAYS=7 APPLY=1 python manage.py shell < scripts/set_offering_days.py  # other value

Notes:
  * Default DAYS=5. duration_months follows Offering.normalize_durations():
    months = days/30 only for an exact multiple of 30, otherwise empty.
  * Uses .update(): updated_at is NOT touched (no fake "recently modified" badges).
  * total_fee / daily_fee are NOT recalculated.
  * One transaction, idempotent. Back up db first.
"""
import os

from django.db import transaction

from enrollment.models import Offering

DAYS = int(os.environ.get("DAYS", 5))
APPLY = os.environ.get("APPLY") == "1"
MONTHS = DAYS // 30 if DAYS % 30 == 0 else None

todo = Offering.objects.exclude(duration_days=DAYS) | Offering.objects.filter(duration_days__isnull=True)
todo = todo.distinct()
print(f"{todo.count()} / {Offering.objects.count()} offerings to set to {DAYS} days")

if APPLY:
    with transaction.atomic():
        n = todo.update(duration_days=DAYS, duration_months=MONTHS)
    print(f"APPLIED: {n} updated.")
else:
    print("DRY-RUN: nothing written. Re-run with APPLY=1.")
