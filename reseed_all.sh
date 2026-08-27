#!/usr/bin/env bash
# Full re-seed pipeline — run from inside the activated venv, at project root
# (where manage.py lives).
#
# Usage:
#   source venv/bin/activate
#   ./reseed_all.sh
#
# All seed commands below are idempotent (update_or_create / get_or_create),
# so this is safe to re-run at any time — nothing is flushed first.
#
# Order matters:
#   1. seed_data          — base site content + official 2019 nomenclature
#                            (23 branches / ~500 specialties)
#   2. seed_enrollment     — real institutional data from the CSV exports in
#                            docs/ (Branch/Specialty/Formation/Trainer),
#                            layered on top of the nomenclature by code
#   3. seed_samples        — partners, process steps, testimonials
#   4. seed_formateurs      — avatar photo + offering assignment for the
#                            real formateurs imported from the Trainer CSV
#   5. seed_formateur_profiles — certificate/career-timeline placeholders,
#                            only for formateurs an admin has actually
#                            curated (title/bio set) — never fabricated
#                            for CSV-only trainers
#   6. seed_fiche_technique — offering objectives / program / prerequisites
#   7. seed_gallery         — secondary gallery images for sample offerings
#   8. seed_about_faq       — About + FAQ page content
set -euo pipefail

echo "== 1/8: base site content + official nomenclature =="
python manage.py flush
python manage.py seed_data

echo "== 2/8: real institutional data (Branch/Specialty/Formation/Trainer CSVs) =="
python manage.py seed_enrollment

echo "== 3/8: home-page samples (partners, process steps, testimonials) =="
python manage.py seed_samples

echo "== 4/8: formateur profiles + offering assignment =="
python manage.py seed_formateurs

echo "== 5/8: formateur certificates, career timeline, CV placeholders =="
python manage.py seed_formateur_profiles

echo "== 6/8: fiche technique content =="
python manage.py seed_fiche_technique

echo "== 7/8: offering gallery images =="
python manage.py seed_gallery

echo "== 8/8: About + FAQ pages =="
python manage.py seed_about_faq

echo "✓ Full re-seed completed."


# 3. Re-run the batch prep so the ledger knows about the new formation_ids
python manage.py prep_fiche_batches

# 4. Re-seed so Offerings exist for the newly-added codes
python manage.py seed_enrollment

# 5. Now apply — new_formations_candidates.csv is included this time
python manage.py apply_fiche_batches --overwrite