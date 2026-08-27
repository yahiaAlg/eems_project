"""
Step 3 of the fiche-technique content pipeline: reads every completed
batch CSV back from docs/ai_batches_done/, and for each formation:

  1. Looks up its Offering by code in the default catalogue session.
  2. If it doesn't exist yet (e.g. seed_enrollment hasn't been (re)run
     since this formation was added to the CSV) — creates it first,
     using the same defaulting rules as seed_enrollment.py.
  3. Writes description / objectives / program_outline / main_tasks /
     prerequisites onto it.
  4. Marks the ledger row "done".

Idempotent + non-destructive by default: a field already containing text
is left untouched unless --overwrite is passed. Blank AI-filled fields
never overwrite existing content either way.

Usage:
    python manage.py apply_fiche_batches                    # all files in docs/ai_batches_done/
    python manage.py apply_fiche_batches batch_03.csv        # just one
    python manage.py apply_fiche_batches --overwrite         # replace existing text too
    python manage.py apply_fiche_batches --dry-run
"""

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.db import transaction

from enrollment.management._fiche_batch_lib import (
    CONTENT_FIELDS,
    DONE_DIR_NAME,
    load_ledger,
    read_completed_batch,
    save_ledger,
)
from enrollment.models import FormationSession, Offering

CSV_DIR = django_settings.BASE_DIR / "docs"
DEFAULT_SESSION_SLUG = "catalogue-eems"  # matches seed_enrollment.py::seed_session


def _get_or_create_offering(session, row):
    """Mirrors seed_enrollment.py's offering defaults for the rare case a
    formation reaches this step without ever having been through
    seed_enrollment (e.g. added to the CSV afterwards)."""
    offering = Offering.objects.filter(session=session, code=row["code"]).first()
    if offering:
        return offering, False

    try:
        duration_days = int(row.get("duration_days") or 0)
    except ValueError:
        duration_days = 0
    duration_months = max(1, round(duration_days / 30)) if duration_days else 1

    try:
        seats = int(row.get("max_participants") or 0)
    except ValueError:
        seats = 0

    offering = Offering.objects.create(
        session=session,
        code=row["code"],
        title=row.get("title_ar", "").strip() or row.get("title", "").strip(),
        branch_label=row.get("category_name", "").strip() or "تكوين عام",
        duration_months=duration_months,
        seats_available=seats,
        is_active=True,
        order=int(row["formation_id"]),
    )
    return offering, True


class Command(BaseCommand):
    help = "Apply completed fiche-technique AI batch CSVs to the Offering model."

    def add_arguments(self, parser):
        parser.add_argument(
            "files", nargs="*",
            help="Specific filenames in docs/ai_batches_done/ to apply. Default: all of them.",
        )
        parser.add_argument("--overwrite", action="store_true", help="Replace non-blank existing content fields.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would happen, write nothing.")

    def handle(self, *args, **options):
        done_dir = CSV_DIR / DONE_DIR_NAME
        if options["files"]:
            paths = [done_dir / name for name in options["files"]]
        else:
            paths = sorted(done_dir.glob("*.csv")) if done_dir.exists() else []

        if not paths:
            self.stdout.write(self.style.WARNING(f"↷ No batch files found in {done_dir}/"))
            return

        session = FormationSession.objects.filter(slug=DEFAULT_SESSION_SLUG).first()
        if session is None:
            self.stdout.write(self.style.ERROR(
                "✗ No FormationSession found — run seed_enrollment first."
            ))
            return

        ledger = load_ledger(CSV_DIR)
        updated, created_offerings, skipped_rows, all_problems = 0, 0, 0, []

        for path in paths:
            valid_rows, problems = read_completed_batch(path)
            all_problems.extend(problems)

            for row in valid_rows:
                with transaction.atomic():
                    offering, was_created = _get_or_create_offering(session, row)
                    created_offerings += 1 if was_created else 0

                    changed = False
                    for cf in CONTENT_FIELDS:
                        value = row.get(cf, "").strip()
                        if not value:
                            continue
                        current = getattr(offering, cf) or ""
                        if current.strip() and not options["overwrite"]:
                            continue
                        setattr(offering, cf, value)
                        changed = True

                    if changed and not options["dry_run"]:
                        offering.save(update_fields=CONTENT_FIELDS)
                        updated += 1
                    elif changed:
                        updated += 1  # count only, dry-run

                    fid = row["formation_id"]
                    if fid in ledger and not options["dry_run"]:
                        ledger[fid]["status"] = "done"
                        ledger[fid]["content_source"] = "ai"
                        ledger[fid]["batch_file"] = path.name
                    elif fid not in ledger:
                        skipped_rows += 1

        if not options["dry_run"]:
            save_ledger(CSV_DIR, ledger)

        for p in all_problems:
            self.stdout.write(self.style.WARNING(f"  ⚠ skipped incomplete row — {p}"))

        prefix = "[DRY RUN] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}✔ {updated} offering(s) updated ({created_offerings} newly created), "
            f"{len(all_problems)} row(s) skipped as incomplete."
        ))
        if skipped_rows:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ {skipped_rows} row(s) had a formation_id not present in the ledger "
                f"— run prep_fiche_batches again first."
            ))
