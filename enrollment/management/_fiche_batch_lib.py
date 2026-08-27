"""
Pure stdlib logic for the fiche-technique parallel-AI content pipeline.

Deliberately has ZERO Django imports so it can be unit-tested / run
standalone (`python3 _fiche_batch_lib.py --help`-style) without a working
DB or settings module. The two management commands
(`prep_fiche_batches.py` and `apply_fiche_batches.py`) are thin wrappers
around the functions here.

Pipeline
--------
1. `prep_fiche_batches`  reads docs/Formation-2026-08-23.csv (source of
   truth for which formations exist) + docs/fiche_technique_progress.csv
   (our ledger of what's already been authored). Any formation missing
   from the ledger is added as "pending" (= "if the formation doesn't
   exist in the seed, create it first"). All pending rows are then split
   into N batch CSVs under docs/ai_batches/, each with the raw CSV facts
   + 5 empty content columns for an AI worker to fill in.

2. Each batch CSV is handed to one AI instance in parallel. The AI fills
   the 5 content columns in place (see docs/FICHE_TECHNIQUE_AI_BRIEF.md
   for the schema/style rules) and saves the file to
   docs/ai_batches_done/.

3. `apply_fiche_batches` reads every completed batch back, upserts the
   Offering (creating it first via the same logic as seed_enrollment.py
   if it somehow doesn't exist yet), writes the 5 content fields, and
   flips the ledger row to "done".

Re-running `prep_fiche_batches` at any point is safe: it only ever adds
rows for formations that aren't in the ledger yet, it never touches rows
already marked "done".
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

FORMATION_CSV = "Formation-2026-08-23.csv"
LEDGER_CSV = "fiche_technique_progress.csv"
BATCH_DIR_NAME = "ai_batches"
DONE_DIR_NAME = "ai_batches_done"

# Hand-curated demo offerings from the Sept 2025 session — never touched
# by CSV-driven seeding (see seed_enrollment.py::LEGACY_CODES). Two of
# them (MME07Q, TAG0701, TAG0704) aren't even rows in the Formation CSV.
LEGACY_CODES = {"CIP01Q", "MME07Q", "TAG0701", "TAG0704"}

# The 5 Offering text fields that make up the fiche technique (see
# enrollment/models.py::Offering + templates/.../fiche_technique_placeholder.html).
# Each is stored as ONE ITEM PER LINE (Offering.objectives_list etc. just
# does `.splitlines()`), so in the CSV these are quoted multi-line cells.
CONTENT_FIELDS = ["description", "objectives", "program_outline", "main_tasks", "prerequisites"]

# Read-only facts copied from the Formation CSV into every batch row, so
# an AI worker never has to cross-reference the source CSV by hand.
CONTEXT_FIELDS = [
    "formation_id", "code", "title", "title_ar", "category_name",
    "attestation_type", "duration_days", "duration_hours",
    "min_participants", "max_participants", "evaluation_type",
    "produces_certificate", "accreditation_body", "legal_references",
]

LEDGER_FIELDS = ["formation_id", "code", "title", "status", "content_source", "batch_file"]


# ---------------------------------------------------------------------
# Formation CSV loading (mirrors seed_enrollment.py's code-dedup rule)
# ---------------------------------------------------------------------

def read_formation_rows(csv_dir: Path) -> list[dict]:
    with open(csv_dir / FORMATION_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    code_counts = Counter(r["code"].strip() for r in rows)
    for r in rows:
        base_code = r["code"].strip() or f"FORM{r['id']}"
        # Same disambiguation seed_enrollment.py applies when a code repeats
        # (e.g. "CIP1202" is reused by CPHS / Lutte Incendie / Premier Secours).
        r["_effective_code"] = base_code if code_counts[base_code] == 1 else f"{base_code}-{r['id']}"
    return rows


# ---------------------------------------------------------------------
# Ledger (docs/fiche_technique_progress.csv) — the persistent memory of
# what's already been authored, across however many prep/apply runs.
# ---------------------------------------------------------------------

def load_ledger(csv_dir: Path) -> dict[str, dict]:
    path = csv_dir / LEDGER_CSV
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["formation_id"]: row for row in csv.DictReader(f)}


def save_ledger(csv_dir: Path, ledger: dict[str, dict]) -> None:
    path = csv_dir / LEDGER_CSV
    rows = sorted(ledger.values(), key=lambda r: int(r["formation_id"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------
# Step 1 — sync: add any formation missing from the ledger ("create it
# first"), skip ones already legacy/done. Returns the still-pending rows.
# ---------------------------------------------------------------------

@dataclass
class SyncResult:
    newly_registered: list[dict] = field(default_factory=list)
    pending: list[dict] = field(default_factory=list)
    already_done: int = 0
    legacy_skipped: int = 0


def sync_ledger_with_formations(formation_rows: list[dict], ledger: dict[str, dict]) -> SyncResult:
    result = SyncResult()
    for row in formation_rows:
        fid = row["id"]
        code = row["code"].strip()

        if code in LEGACY_CODES:
            if fid not in ledger:
                ledger[fid] = dict(
                    formation_id=fid, code=code, title=row["title"],
                    status="done", content_source="legacy_curated", batch_file="",
                )
            result.legacy_skipped += 1
            continue

        existing = ledger.get(fid)
        if existing is None:
            # Formation not in our seed/ledger yet -> register it first,
            # as "pending", before it can get its fiche technique content.
            entry = dict(
                formation_id=fid, code=row["_effective_code"], title=row["title"],
                status="pending", content_source="", batch_file="",
            )
            ledger[fid] = entry
            result.newly_registered.append(row)
            result.pending.append(row)
        elif existing["status"] != "done":
            result.pending.append(row)
        else:
            result.already_done += 1

    return result


# ---------------------------------------------------------------------
# Step 2 — split pending formations into N batch CSVs for parallel AIs.
# ---------------------------------------------------------------------

def write_batches(pending_rows: list[dict], batch_dir: Path, batch_size: int) -> list[Path]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = CONTEXT_FIELDS + CONTENT_FIELDS
    paths = []

    for i in range(0, len(pending_rows), batch_size):
        chunk = pending_rows[i : i + batch_size]
        batch_num = i // batch_size + 1
        path = batch_dir / f"batch_{batch_num:02d}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in chunk:
                out = {k: row.get(k, "") for k in CONTEXT_FIELDS}
                out["formation_id"] = row["id"]
                out["code"] = row["_effective_code"]
                for cf in CONTENT_FIELDS:
                    out[cf] = ""  # left blank for the AI worker to fill
                writer.writerow(out)
        paths.append(path)

    return paths


# ---------------------------------------------------------------------
# Step 3 — read a completed batch back, validate it's actually filled in.
# ---------------------------------------------------------------------

def read_completed_batch(path: Path) -> tuple[list[dict], list[str]]:
    """Returns (valid_rows, problems). A row is only rejected (with a
    reason appended to `problems`) if description/objectives/program_outline
    are still blank — main_tasks and prerequisites may legitimately be
    empty for some formations."""
    required = ["description", "objectives", "program_outline"]
    valid_rows, problems = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            missing = [field_ for field_ in required if not row.get(field_, "").strip()]
            if missing:
                problems.append(f"{path.name}: formation_id={row.get('formation_id')} missing {missing}")
                continue
            valid_rows.append(row)
    return valid_rows, problems
