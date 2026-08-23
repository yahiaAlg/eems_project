import csv
from collections import Counter
from pathlib import Path

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand

from enrollment.models import FormationSession, Offering, Formateur
from pages.models import Branch, Specialty

CSV_DIR = Path(django_settings.BASE_DIR) / "docs"

# These 4 codes were hand-curated (rich Arabic descriptions, images, an existing
# accepted enrollment and assigned formateurs) for the September 2025 demo
# session. We never touch/overwrite them here — everything else from the real
# CSV exports is added alongside them in a separate, general session.
LEGACY_CODES = {"CIP01Q", "MME07Q", "TAG0701", "TAG0704"}


def read_csv(name):
    with open(CSV_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Command(BaseCommand):
    help = (
        "يعبئ قاعدة البيانات بالبيانات الحقيقية لمؤسسة إيمس (الفروع، التخصصات، "
        "عروض التكوين، والمكوّنون) انطلاقا من ملفات CSV الموجودة في docs/ "
        "(Branch / Specialty / Formation / Trainer). لا يمس هذا الأمر عروض "
        "التكوين الأربعة المنسّقة يدويا لدورة سبتمبر 2025."
    )

    def handle(self, *args, **options):
        branches = self.seed_branches()
        specialties_by_id = self.seed_specialties(branches)
        session = self.seed_session()
        self.seed_offerings(session, specialties_by_id)
        self.seed_formateurs()
        self.stdout.write(self.style.SUCCESS("تم تحميل بيانات إيمس الحقيقية من ملفات CSV بنجاح."))

    # ------------------------------------------------------------------
    def seed_branches(self):
        branches = {}
        for row in read_csv("Branch-2026-08-23.csv"):
            branch, _ = Branch.objects.update_or_create(
                code=row["abbreviation"],
                defaults=dict(
                    name_ar=row["name_ar"],
                    name_fr=row["name"],
                    is_active=True,
                ),
            )
            branches[row["abbreviation"]] = branch
        self.stdout.write(self.style.SUCCESS(f"  ✔ {len(branches)} فرع (Branch CSV)"))
        return branches

    # ------------------------------------------------------------------
    def seed_specialties(self, branches):
        by_id = {}
        for row in read_csv("Specialty-2026-08-23.csv"):
            branch = branches.get(row["branch_abbreviation"])
            if not branch:
                continue
            code = f"{row['branch_abbreviation']}{row['code']}"
            name = row["title_ar"].strip() or row["title"].strip()
            specialty, _ = Specialty.objects.update_or_create(
                code=code,
                defaults=dict(name=name, branch=branch),
            )
            by_id[row["id"]] = specialty
        self.stdout.write(self.style.SUCCESS(f"  ✔ {len(by_id)} تخصص (Specialty CSV)"))
        return by_id

    # ------------------------------------------------------------------
    def seed_session(self):
        session, _ = FormationSession.objects.update_or_create(
            slug="catalogue-eems",
            defaults=dict(
                name="الكتالوج العام لتكوينات إيمس",
                is_active=True,
                order=0,
            ),
        )
        return session

    # ------------------------------------------------------------------
    def seed_offerings(self, session, specialties_by_id):
        rows = read_csv("Formation-2026-08-23.csv")
        code_counts = Counter(r["code"].strip() for r in rows)

        # A handful of certificate-producing courses get featured on the home page.
        featured_ids = {
            r["id"] for r in rows
            if r["produces_certificate"] == "1" and r["code"].strip() not in LEGACY_CODES
        }
        featured_ids = set(list(featured_ids)[:4])

        created = 0
        for row in rows:
            base_code = row["code"].strip() or f"FORM{row['id']}"
            if base_code in LEGACY_CODES:
                continue  # preserve curated demo content untouched

            code = base_code if code_counts[base_code] == 1 else f"{base_code}-{row['id']}"

            specialty = None
            specialty_id = row["specialty_id"].strip()
            if specialty_id:
                specialty = specialties_by_id.get(specialty_id)
            if specialty is None:
                specialty = Specialty.objects.filter(code=base_code).first()

            title = row["title_ar"].strip() or row["title"].strip()
            category = row["category_name"].strip()
            branch_label = (specialty.branch.name_ar if specialty else "") or category or "تكوين عام"

            try:
                duration_days = int(row["duration_days"] or 0)
            except ValueError:
                duration_days = 0
            duration_months = max(1, round(duration_days / 30)) if duration_days else 1

            try:
                seats = int(row["max_participants"] or 0)
            except ValueError:
                seats = 0

            description = f"دورة تكوينية ضمن مجال {category}." if category else ""
            if duration_days:
                hours = row["duration_hours"].strip()
                description += f" المدة: {duration_days} يوم ({hours} ساعة تكوين)."

            Offering.objects.update_or_create(
                session=session, code=code,
                defaults=dict(
                    title=title,
                    branch_label=branch_label,
                    specialty=specialty,
                    duration_months=duration_months,
                    seats_available=seats,
                    description=description.strip(),
                    is_active=True,
                    is_featured=row["id"] in featured_ids,
                    order=int(row["id"]),
                ),
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"  ✔ {created} عرض تكوين (Formation CSV)"))

    # ------------------------------------------------------------------
    def seed_formateurs(self):
        created = 0
        for row in read_csv("Trainer-2026-08-23.csv"):
            first_ar = row["first_name_ar"].strip()
            last_ar = row["last_name_ar"].strip()
            full_name = (
                f"{first_ar} {last_ar}".strip() if (first_ar or last_ar)
                else f"{row['first_name'].strip()} {row['last_name'].strip()}".strip()
            )
            if not full_name:
                continue
            _, is_new = Formateur.objects.get_or_create(
                full_name=full_name,
                defaults=dict(is_active=row["is_active"] == "1"),
            )
            created += 1 if is_new else 0
        self.stdout.write(self.style.SUCCESS(f"  ✔ {created} مكوّن جديد (Trainer CSV)"))
