"""
Step 1 of the fiche-technique content pipeline: figures out which
formations still need a fiche technique (checking the seed/ledger first
and registering any formation that's missing from it), then splits the
pending ones into batch CSVs so several AI instances can write the
content in parallel.

Follows the exact same "read CSV from docs/" convention as
seed_enrollment.py / seed_fiche_technique.py.

Usage:
    python manage.py prep_fiche_batches
    python manage.py prep_fiche_batches --batch-size 10
    python manage.py prep_fiche_batches --workers 12   # split evenly across N AIs instead

Safe to re-run: only formations not yet in docs/fiche_technique_progress.csv
are (re)batched; anything already marked "done" in the ledger is skipped.
"""

import math

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand

from enrollment.management._fiche_batch_lib import (
    BATCH_DIR_NAME,
    read_formation_rows,
    load_ledger,
    save_ledger,
    sync_ledger_with_formations,
    write_batches,
)

CSV_DIR = django_settings.BASE_DIR / "docs"


class Command(BaseCommand):
    help = "Prepare parallel-AI batch CSVs for the fiche techniques still missing content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size", type=int, default=12,
            help="Formations per batch file (default: 12). Ignored if --workers is given.",
        )
        parser.add_argument(
            "--workers", type=int, default=None,
            help="Split the pending formations evenly across exactly N batch files "
                 "(one per parallel AI instance), instead of using --batch-size.",
        )

    def handle(self, *args, **options):
        formation_rows = read_formation_rows(CSV_DIR)
        ledger = load_ledger(CSV_DIR)

        result = sync_ledger_with_formations(formation_rows, ledger)
        save_ledger(CSV_DIR, ledger)

        if result.newly_registered:
            self.stdout.write(self.style.SUCCESS(
                f"  ✔ {len(result.newly_registered)} formation(s) were missing from the seed/ledger "
                f"— registered as pending: "
                + ", ".join(r['code'].strip() or r['id'] for r in result.newly_registered[:8])
                + (" ..." if len(result.newly_registered) > 8 else "")
            ))

        self.stdout.write(
            f"  · {result.already_done} already done · "
            f"{result.legacy_skipped} legacy (hand-curated, skipped) · "
            f"{len(result.pending)} pending"
        )

        if not result.pending:
            self.stdout.write(self.style.SUCCESS("✔ Nothing pending — every formation has a fiche technique."))
            return

        batch_size = options["batch_size"]
        if options["workers"]:
            batch_size = max(1, math.ceil(len(result.pending) / options["workers"]))

        batch_dir = CSV_DIR / BATCH_DIR_NAME
        paths = write_batches(result.pending, batch_dir, batch_size)

        self.stdout.write(self.style.SUCCESS(
            f"✔ Wrote {len(paths)} batch file(s) to {batch_dir}/ "
            f"({len(result.pending)} formations, ~{batch_size}/batch)."
        ))
        self.stdout.write(
            "  Hand one file per AI instance along with "
            "docs/FICHE_TECHNIQUE_AI_BRIEF.md. Save completed files to "
            "docs/ai_batches_done/ with the same filename, then run "
            "`python manage.py apply_fiche_batches`."
        )
