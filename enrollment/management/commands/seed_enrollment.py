from datetime import date

from django.core.management.base import BaseCommand

from enrollment.models import FormationSession, Offering


class Command(BaseCommand):
    help = "يعبئ قاعدة البيانات ببيانات دورة سبتمبر 2025 (مطابقة لملصقات EEMS الترويجية)."

    def handle(self, *args, **options):
        session, _ = FormationSession.objects.update_or_create(
            slug="septembre-2025",
            defaults=dict(
                name="الدخول المهني — دورة سبتمبر 2025",
                start_date=date(2025, 9, 1),
                registration_deadline=date(2025, 9, 20),
                is_active=True,
                order=1,
            ),
        )

        offerings = [
            dict(
                code="CIP01Q", title="عون الوقاية والأمن",
                branch_label="الكيمياء الصناعية والبلاستيك",
                qualification_level=None, certificate_type="qualification",
                entry_level="sec3", duration_months=6,
                monthly_fee=10000, total_fee=60000, seats_available=15,
                description=(
                    "يعمل عون الوقاية تحت سلطة رئيسه على احترام قواعد الأمن داخل "
                    "المنشآت ووقاية العمال والمعدات من حوادث العمل."
                ),
                main_tasks=(
                    "إتقان أساليب المراقبة والتدخل والإجراءات الوقائية للحوادث\n"
                    "معرفة قوانين وتشريعات السلامة والصحة المهنية والبيئية\n"
                    "تحديد وتقييم المخاطر وطرق الوقاية في مكان العمل\n"
                    "رصد فعالية تطبيق قواعد السلامة من طرف المهنيين\n"
                    "المساعدة في إدارة الأزمة بعد وقوع الحادث\n"
                    "المشاركة في دورة IOSH Managing البريطانية"
                ),
                order=1,
            ),
            dict(
                code="MME07Q", title="سائق رافعة الأثقال",
                branch_label="ميكانيك المحركات والآلات",
                qualification_level=None, certificate_type="qualification",
                entry_level="none", duration_months=3,
                monthly_fee=8000, total_fee=24000, seats_available=12,
                description="تكوين تأهيلي لقيادة الرافعة الشوكية (Chariot élévateur) وفق معايير السلامة.",
                main_tasks="قيادة الرافعة الشوكية بأمان\nمناولة ونقل البضائع داخل المخازن\nاحترام قواعد السلامة أثناء المناولة",
                order=2,
            ),
            dict(
                code="TAG0701", title="أمين مخزن (Magasinier)",
                branch_label="تقنيات الإدارة والتسيير",
                qualification_level=2, certificate_type="bpm",
                entry_level="middle4", duration_months=12,
                monthly_fee=10000, total_fee=120000, seats_available=12,
                description=(
                    "يتولى القيام بالواجبات والمهام المتعلقة بتخزين البضائع، "
                    "ينظم المخزن ويحافظ على سلامته."
                ),
                main_tasks=(
                    "استقبال وفحص البضائع الواردة\n"
                    "تجهيز طلبات العملاء وشحنها\n"
                    "ضبط ومراقبة ما يخرج من المخزن\n"
                    "القيام بعمليات الجرد الدورية\n"
                    "إدارة وتنسيق مساحات التخزين"
                ),
                order=3,
            ),
            dict(
                code="TAG0704", title="التأمينات",
                branch_label="تقنيات الإدارة والتسيير",
                qualification_level=3, certificate_type="bpm",
                entry_level="middle4", duration_months=18,
                monthly_fee=12000, total_fee=216000, seats_available=12,
                description=(
                    "يقدم استشارات ومعلومات للزبائن الخواص والمؤسسات حول منتوج "
                    "التأمينات (الحريق، الحياة...)."
                ),
                main_tasks=(
                    "الإشراف على سوق التأمين (استشارة ومساعدة)\n"
                    "بيع منتوجات التأمينات\n"
                    "التحاور مع الزبائن لتحديد نمط التأمين وشروط الضمانات\n"
                    "متابعة ملفات الزبائن وتقييم المخاطر"
                ),
                order=4,
            ),
        ]

        for data in offerings:
            code = data.pop("code")
            title = data.pop("title")
            Offering.objects.update_or_create(
                session=session, code=code,
                defaults=dict(title=title, is_active=True, **data),
            )
            self.stdout.write(self.style.SUCCESS(f"✔ {code} — {title}"))

        self.stdout.write(self.style.SUCCESS("تم تحميل بيانات دورة سبتمبر 2025 بنجاح."))
