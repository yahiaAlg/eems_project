import csv
import datetime
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.conf import settings as django_settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import (
    SiteSettings,
    HeroStat,
    MissionCard,
    CarouselImage,
    Branch,
    Specialty,
    TrainingSession,
    SocialLink,
    InternalApp,
    NavLink,
)

CSV_DIR = Path(django_settings.BASE_DIR) / "docs"


def _read_csv(name):
    with open(CSV_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Brand colors kept per branch code (falls back to a neutral slate for any
# new branch code that shows up in a future CSV export without a color yet).
_BRANCH_COLORS = {
    "BTP": "#1D4ED8",
    "CIP": "#0E7490",
    "CMS": "#4B5563",
    "ELE": "#D97706",
    "INT": "#2563EB",
    "MEE": "#0891B2",
    "MIC": "#6B7280",
    "MME": "#1F2937",
    "TAG": "#7C3AED",
}


def _load_branches_and_specialties():
    """Build the (code, name_ar, name_fr, color) / (code, name, branch_code)
    seed tuples straight from the institute's real CSV exports (docs/), so
    the seeded catalogue always matches what EEMS actually teaches instead
    of a stale hardcoded snapshot of the national 2019 nomenclature.
    """
    branches = [
        (
            row["abbreviation"],
            row["name_ar"],
            row["name"],
            _BRANCH_COLORS.get(row["abbreviation"], "#334155"),
        )
        for row in _read_csv("Branch-2026-08-23.csv")
    ]
    specialties = [
        (
            f"{row['branch_abbreviation']}{row['code']}",
            row["title_ar"].strip() or row["title"].strip(),
            row["branch_abbreviation"],
        )
        for row in _read_csv("Specialty-2026-08-23.csv")
    ]
    return branches, specialties


BRANCHES, SPECIALTIES = _load_branches_and_specialties()


class Command(BaseCommand):
    help = "Seed the database with the original EEMS static-site content (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.seed_admin_user()
        self.seed_site_settings()
        self.seed_images()
        self.seed_hero_stats()
        self.seed_mission_cards()
        self.seed_branches_and_specialties()
        self.seed_sessions()
        self.seed_social_links()
        self.seed_internal_apps()
        self.seed_nav_links()
        self.stdout.write(self.style.SUCCESS("✔ Seed data loaded successfully."))

    # ── Admin (superuser) account ───────────────────────────────
    # Idempotent: only creates the account the first time; never resets the
    # password of an existing account on re-run. Override the credentials via
    # env vars EEMS_ADMIN_USERNAME / EEMS_ADMIN_EMAIL / EEMS_ADMIN_PASSWORD
    # before running seed_data if you don't want the default password.
    def seed_admin_user(self):
        User = get_user_model()
        username = os.environ.get("EEMS_ADMIN_USERNAME", "admin")
        email = os.environ.get("EEMS_ADMIN_EMAIL", "admin@eems.dz")
        password = os.environ.get("EEMS_ADMIN_PASSWORD", "system2026*")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ تم إنشاء حساب المدير: {username} / {password} "
                    f"— يُنصح بتغيير كلمة المرور فورا من لوحة التحكم."
                )
            )
        else:
            # Make sure an existing account keeps admin rights even if it
            # was created manually without them.
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if changed:
                user.save()
            self.stdout.write(
                self.style.WARNING(f"↷ حساب المدير موجود مسبقا: {username}")
            )

    # ── SiteSettings (singleton) ────────────────────────────────
    def seed_site_settings(self):
        s = SiteSettings.load()
        s.site_name = "إيمس"
        s.site_full_name = "مؤسسة التميز للإدارة والسلامة"
        s.browser_title = "إيمس — مؤسسة التميز للإدارة والسلامة"

        s.hero_badge_text = "معتمدة من وزارة التكوين والتعليم المهنيين"
        s.hero_title_line1 = "مؤسسة التميز"
        s.hero_title_line2 = "للإدارة"
        s.hero_title_accent = "والسلامة"
        s.hero_description = (
            "مؤسسة خاصة للتكوين والتعليم المهني معتمدة بسطيف — 15 فرعا: إدارية، إعلام آلي ومهن "
            "مهنية، مع مكتب دراسات معتمد من وزارة البيئة."
        )
        s.hero_cta_primary_text = "سجّل في تكويناتنا"
        s.hero_cta_primary_url = "/formations/"
        s.hero_cta_secondary_text = "التصنيف الرسمي"
        s.hero_cta_secondary_url = "/nomenclature/"

        s.formations_label = "الكتالوج الرسمي 2019"
        s.formations_title = "23 فرعا مهنيا"
        s.formations_description = (
            "تغطي مؤسسة إيمس مجمل فروع الكتالوج الرسمي الجزائري للتكوين المهني. "
            "اطّلع على التصنيف الكامل للوصول إلى أكثر من 500 تخصص."
        )

        s.video_label = "اكتشف"
        s.video_title = "المسير العملي"
        s.video_description = "دور أساسي في الوقاية من أخطر المخاطر داخل المؤسسة."
        s.video_youtube_embed_url = (
            "https://www.youtube.com/embed/1h4-kRB8OjA?si=6XjJKFKHlIqeWta_"
        )

        s.gallery_label = "معرض الصور"
        s.gallery_title = "مرحبا بكم في إيمس"

        s.map_label = "الموقع"
        s.map_title = "كيف تجدنا"
        s.map_description = (
            "يمكن الوصول إلينا من محطة النقل الرئيسية بسطيف بواسطة الحافلة رقم 7 أو سيارة الأجرة — "
            "حوالي 6 كم، 15 دقيقة."
        )
        s.map_embed_url = (
            "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3219.4966084436987!2d5.428236791294961"
            "!3d36.20312261143598!2m3!1f0!2f0!3f0!3m2!1f0!2i768!4f13.1!3m3!1m2!1s0x12f3153200865125"
            "%3A0xa4cf0a1a7a40cfb5!2z2YXYpNiz2LPYqSDYp9mE2KrZhdmK2LIg2YjYp9mE2KrYp9ix2Kkg2YjYp9mE2LPZhNin2YXYqQ"
            "!5e0!3m2!1sar!2sdz!4v1721223880342!5m2!1sar!2sdz"
        )

        s.address = "الطريق الوطني رقم 1، سطيف 19135، الجزائر"
        s.phone = ""
        s.email = "contact@eems.dz"
        s.working_hours = "الأحد – الخميس: 08:00 – 16:30"

        s.footer_description = (
            "إيمس (EEMS) — مؤسسة التميز للإدارة والسلامة — مؤسسة خاصة للتكوين والتعليم المهني "
            "معتمدة، متخصصة في مجالات الصحة والسلامة والبيئة (HSE) والتقنية والتسيير. "
            "سطيف، الجزائر."
        )
        s.footer_copyright = (
            "© 2025 إيمس — مؤسسة التميز للإدارة والسلامة — جميع الحقوق محفوظة."
        )
        s.footer_location_text = "سطيف، الجزائر"
        s.save()

    # ── Hero stats ───────────────────────────────────────────────
    def seed_hero_stats(self):
        HeroStat.objects.all().delete()
        for value, label, order in [
            ("15", "فرعا", 1),
            ("+500", "تخصصا", 2),
            ("+15", "سنوات خبرة", 3),
        ]:
            HeroStat.objects.create(value=value, label=label, order=order)

    # ── Mission / Vision / Compétences ──────────────────────────
    def seed_mission_cards(self):
        MissionCard.objects.all().delete()
        cards = [
            (
                "bi bi-bullseye",
                "amber",
                "مهمتنا",
                (
                    "تهدف مؤسسة إيمس إلى تكوين مسيرين ومشرفين في مجال الصحة والسلامة والبيئة (HSE) "
                    "قادرين على تقديم إضافة نوعية في هذا المجال، وتوجيه المترشحين نحو فترات تدريبية "
                    "عملية داخل مختلف المؤسسات لضمان اندماج تدريجي في عالم الشغل. يتم تتبع المترشحين "
                    "من خلال قسم مخصص لتسيير المسار المهني والتكوين ومرافقة المؤسسات."
                ),
            ),
            (
                "bi bi-eye-fill",
                "green",
                "رؤيتنا",
                (
                    "تتمثل رؤيتنا في إبراز التحديات الحقيقية لمنظومة إدارة الصحة والسلامة والبيئة، "
                    "من خلال تحليل وضعية المؤسسات ودراسة مستويات استيعاب مفاهيم الجودة–الصحة–البيئة، "
                    "وكذا تناسقها من أجل مقاربة ناجحة."
                ),
            ),
            (
                "bi bi-graph-up-arrow",
                "blue",
                "كفاءاتنا",
                (
                    "يكرّس جميع مكوّني إيمس جهودهم لإنشاء وتصميم وتطوير برامج جديدة في مجال الصحة "
                    "والسلامة والبيئة وفق أحدث الأساليب والتقنيات الدولية ونظم إدارة QSE. كما يقومون "
                    "بتدقيق الأداء للتحقق من فعالية أساليب التكوين، وجمع آراء المشرفين الميدانيين "
                    "العاملين فعلا في هذا المجال."
                ),
            ),
        ]
        for i, (icon, color, title, text) in enumerate(cards, start=1):
            MissionCard.objects.create(
                icon_class=icon, color=color, title=title, text=text, order=i
            )

    # ── Branches + Specialties (official 2019 nomenclature) ─────
    def seed_branches_and_specialties(self):
        valid_branch_codes = {code for code, *_ in BRANCHES}
        valid_specialty_codes = {code for code, *_ in SPECIALTIES}

        branch_map = {}
        for i, (code, name_ar, name_fr, color) in enumerate(BRANCHES, start=1):
            branch, _ = Branch.objects.update_or_create(
                code=code,
                defaults=dict(name_ar=name_ar, name_fr=name_fr, color=color, order=i),
            )
            branch_map[code] = branch

        for code, name, branch_code in SPECIALTIES:
            branch = branch_map.get(branch_code)
            if not branch:
                continue
            Specialty.objects.update_or_create(
                code=code, defaults=dict(name=name, branch=branch),
            )

        # Purge anything left over from a previous/stale seed (e.g. the full
        # national nomenclature this project used to ship with) that isn't
        # part of the institute's real catalogue above. Any Offering still
        # pointing at a stale specialty is unlinked (set to null) rather
        # than deleted — the course itself is real, only its specialty tag
        # was wrong.
        from enrollment.models import Offering

        stale_specialties = Specialty.objects.exclude(code__in=valid_specialty_codes)
        Offering.objects.filter(specialty__in=stale_specialties).update(specialty=None)
        stale_specialties.delete()
        Branch.objects.exclude(code__in=valid_branch_codes).delete()

    # ── Upcoming sessions ────────────────────────────────────────
    def seed_sessions(self):
        """Upcoming-courses strip: real HSE + IT formations pulled straight
        from the Formation CSV export (picked by stable id), instead of
        made-up titles that don't correspond to anything EEMS runs.
        """
        TrainingSession.objects.all().delete()

        formations = {row["id"]: row for row in _read_csv("Formation-2026-08-23.csv")}
        specialty_branch = {
            row["id"]: row["branch_abbreviation"]
            for row in _read_csv("Specialty-2026-08-23.csv")
        }
        branch_by_code = {b.code: b for b in Branch.objects.all()}

        year = datetime.date.today().year
        # (formation id, upcoming start date, status) — a mix of HSE and IT
        # courses, spread across the year.
        picks = [
            ("57", datetime.date(year, 4, 14), "planned"),  # Atmosphère Explosive (HSE)
            ("50", datetime.date(year, 5, 12), "planned"),  # Habilitation Électrique (HSE)
            ("52", datetime.date(year, 6, 2), "open"),      # Premier Secours (HSE)
            ("68", datetime.date(year, 9, 1), "open"),      # Power BI (Informatique)
            ("67", datetime.date(year, 10, 5), "open"),     # Excel & Word Avancés (Informatique)
        ]

        for i, (formation_id, start_date, status) in enumerate(picks, start=1):
            row = formations.get(formation_id)
            if not row:
                continue
            try:
                duration_days = int(row["duration_days"] or 0)
            except ValueError:
                duration_days = 0
            try:
                seats = int(row["max_participants"] or 0)
            except ValueError:
                seats = 0

            if duration_days == 1:
                duration_text = "يوم واحد"
            elif 2 <= duration_days <= 10:
                duration_text = f"{duration_days} أيام"
            else:
                duration_text = f"{duration_days} يوما"

            branch_code = specialty_branch.get(row["specialty_id"].strip())

            TrainingSession.objects.create(
                title=row["title_ar"].strip() or row["title"].strip(),
                start_date=start_date,
                duration_text=duration_text,
                seats=seats or 20,
                status=status,
                branch=branch_by_code.get(branch_code),
                order=i,
            )

    # ── Social links ─────────────────────────────────────────────
    def seed_social_links(self):
        SocialLink.objects.all().delete()
        links = [
            ("facebook", "https://web.facebook.com/EEMS.SETIF", 1),
            ("linkedin", "#", 2),
            ("instagram", "#", 3),
            ("whatsapp", "#", 4),
            ("email", "mailto:contact@eems.dz", 5),
        ]
        for platform, url, order in links:
            SocialLink.objects.create(platform=platform, url=url, order=order)

    # ── Internal apps ────────────────────────────────────────────
    def seed_internal_apps(self):
        InternalApp.objects.all().delete()
        apps = [
            (
                "تصنيف التكوينات",
                "الكتالوج الرسمي 2019 — أكثر من 500 تخصص",
                "bi bi-list-ul",
                "/nomenclature/",
                "blue",
                False,
                1,
            ),
            (
                "التسجيل الإلكتروني",
                "الدخول المهني — سجّل مباشرة عبر الموقع",
                "bi bi-pencil-square",
                "/formations/",
                "amber",
                False,
                2,
            ),
        ]
        for title, subtitle, icon, url, color, new_tab, order in apps:
            InternalApp.objects.create(
                title=title,
                subtitle=subtitle,
                icon_class=icon,
                url=url,
                color=color,
                open_in_new_tab=new_tab,
                order=order,
            )

    # ── Footer quick-nav links ────────────────────────────────────
    def seed_nav_links(self):
        NavLink.objects.all().delete()
        links = [
            ("الرئيسية", "/", 1),
            ("المهمة والرؤية", "/#mission", 2),
            ("الفروع المهنية", "/#formations", 3),
            ("سجّل في تكوين", "/formations/", 4),
            ("الدورات", "/#sessions", 5),
            ("الاتصال", "/#map-section", 6),
        ]
        for label, url, order in links:
            NavLink.objects.create(label=label, url=url, order=order)

    # ── Images: copy the right static assets into MEDIA ─────────
    #
    # pages/static/pages/images/ holds the original site assets as a flat
    # bundle. Two kinds live there:
    #   - content images (logo, hero photo, gallery photos) → these belong
    #     to admin-editable ImageFields, so we COPY them into MEDIA on first
    #     seed (the admin can then replace them by re-uploading).
    #   - brand/UI icons (Face/Link/Inst/Wats/Twit/Teleg/Snap.png) → these
    #     are fixed site chrome, not admin content, so they STAY in static
    #     and are referenced directly (see SocialLink.static_icon).
    def _find_static_image(self, filename):
        """Locate pages/images/<filename> via the staticfiles finders."""
        relative = f"pages/images/{filename}"
        path = finders.find(relative)
        if not path:
            self.stdout.write(
                self.style.WARNING(f"⚠ static image not found, skipped: {relative}")
            )
        return path

    def seed_images(self):
        s = SiteSettings.load()

        if not s.logo:
            path = self._find_static_image("logo-EEMS.png")
            if path:
                with open(path, "rb") as f:
                    s.logo.save("logo-EEMS.png", File(f), save=False)

        if not s.hero_image:
            path = self._find_static_image("Safety.webp")
            if path:
                with open(path, "rb") as f:
                    s.hero_image.save("Safety.webp", File(f), save=False)

        s.save()

        # Gallery / carousel photos (S1.jpg .. S5.jpg)
        CarouselImage.objects.all().delete()
        for i in range(1, 6):
            filename = f"S{i}.jpg"
            path = self._find_static_image(filename)
            if not path:
                continue
            carousel = CarouselImage(caption=f"صورة إيمس {i}", order=i)
            with open(path, "rb") as f:
                carousel.image.save(filename, File(f), save=False)
            carousel.save()
