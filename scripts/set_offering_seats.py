"""
Set every Offering's capacity (seats_available) to a fixed number.

Usage (from the project folder):
    python manage.py shell < scripts/set_offering_seats.py                 # DRY-RUN
    APPLY=1 python manage.py shell < scripts/set_offering_seats.py         # writes
    SEATS=25 APPLY=1 python manage.py shell < scripts/set_offering_seats.py

Default SEATS=20. Uses .update() (updated_at untouched), one transaction, idempotent.
Back up the db first.
"""
import os

from django.db import transaction

from enrollment.models import Offering

SEATS = int(os.environ.get("SEATS", 20))
APPLY = os.environ.get("APPLY") == "1"

todo = Offering.objects.exclude(seats_available=SEATS)
print(f"{todo.count()} / {Offering.objects.count()} offerings to set to {SEATS} seats")

if APPLY:
    with transaction.atomic():
        n = todo.update(seats_available=SEATS)
    print(f"APPLIED: {n} updated.")
else:
    print("DRY-RUN: nothing written. Re-run with APPLY=1.")
