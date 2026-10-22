"""
Live fix for existing Offering data (no migration needed).

  1) Strip the old "-{ORDER}" suffix from offering codes:
         ELE0702-50 -> ELE0702      CIP1202-47 -> CIP1202
     Hand-made codes such as RH-001 do not match the pattern and are left alone.
  2) Normalize durations (days take priority):
         days set        -> months = days/30 only for an exact multiple, else empty
         only months set -> days   = months * 30

Usage (from the project folder):
    python manage.py shell < scripts/fix_offering_codes.py            # DRY-RUN: only prints
    APPLY=1 python manage.py shell < scripts/fix_offering_codes.py    # really writes

Notes:
  * Uses queryset .update(), so updated_at is NOT touched (no fake "recently modified" badges).
  * Everything runs in one transaction: any error rolls the whole thing back.
  * Idempotent: running it twice changes nothing the second time.
  * Snapshot columns on old invoices/quotes (offering_code) are historical and are not rewritten.
  * Back up first (sqlite: copy db.sqlite3 | postgres: pg_dump).
"""
import os
import re
from collections import Counter

from django.db import transaction

from enrollment.models import Offering

APPLY = os.environ.get("APPLY") == "1"
SUFFIX_RE = re.compile(r"^(?P<base>[A-Za-z]+\d+)-\d+$")  # TAG0701-12, but not RH-001


def clean_code(code, specialty_code):
    """Return the code without its -{ORDER} suffix, or None if nothing to strip."""
    code = (code or "").strip()
    if specialty_code:
        m = re.match(rf"^{re.escape(specialty_code)}-\d+$", code)
        if m:
            return specialty_code
    m = SUFFIX_RE.match(code)
    return m.group("base") if m else None


def clean_durations(days, months):
    """Return (days, months) after normalization."""
    if days:
        return days, (days // 30 if days % 30 == 0 else None)
    if months:
        return months * 30, months
    return None, None


code_changes, duration_changes = [], []
for o in Offering.objects.select_related("specialty").iterator():
    new_code = clean_code(o.code, o.specialty.code if o.specialty_id else "")
    if new_code and new_code != o.code:
        code_changes.append((o.pk, o.code, new_code, o.title))

    nd, nm = clean_durations(o.duration_days, o.duration_months)
    if (nd, nm) != (o.duration_days, o.duration_months):
        duration_changes.append((o.pk, (o.duration_days, o.duration_months), (nd, nm)))

print(f"\n=== codes to clean: {len(code_changes)} ===")
for pk, old, new, title in code_changes:
    print(f"  #{pk:<5} {old:<14} -> {new:<10} {title[:50]}")
print(f"\n=== durations to normalize: {len(duration_changes)} ===")
for pk, old, new in duration_changes[:20]:
    print(f"  #{pk:<5} (days, months) {old} -> {new}")
if len(duration_changes) > 20:
    print(f"  ... and {len(duration_changes) - 20} more")

if not APPLY:
    print("\nDRY-RUN: nothing written. Re-run with APPLY=1 to apply.")
else:
    with transaction.atomic():
        for pk, _old, new, _title in code_changes:
            Offering.objects.filter(pk=pk).update(code=new)
        for pk, _old, (nd, nm) in duration_changes:
            Offering.objects.filter(pk=pk).update(duration_days=nd, duration_months=nm)
    print(f"\nAPPLIED: {len(code_changes)} codes, {len(duration_changes)} durations.")

shared = [c for c, n in Counter(Offering.objects.values_list("code", flat=True)).items() if n > 1]
print(f"(info) codes now shared by several offerings: {len(shared)}\n")
