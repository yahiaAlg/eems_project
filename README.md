# إيمس — Django CMS

تحويل الموقع الثابت (index.html + nomenclature_specialties.html) إلى مشروع Django
كامل، بحيث تتم إدارة كل محتوى الموقع عبر **لوحة تحكم Django Admin** بدل تعديل
كود HTML مباشرة.

## البنية

```
eems_project/
  eems_project/        ← إعدادات المشروع (settings, urls)
  pages/                ← التطبيق الوحيد: كل النماذج + القوالب + لوحة التحكم
    models.py
    admin.py
    views.py
    urls.py
    templates/pages/    ← home.html (الصفحة الرئيسية) و nomenclature.html (الكتالوج)
    management/commands/seed_data.py   ← تعبئة قاعدة البيانات بالمحتوى الأصلي
  requirements.txt
  manage.py
```

## التشغيل

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data        # يحمّل كل المحتوى الأصلي للموقع (23 فرعا + 495 تخصص + ...)
python manage.py createsuperuser
python manage.py runserver
```

- الموقع: http://127.0.0.1:8000/
- الكتالوج: http://127.0.0.1:8000/nomenclature/
- لوحة التحكم: http://127.0.0.1:8000/admin/

## النماذج (Models) وما تتحكم فيه

| النموذج | الغرض |
|---|---|
| `SiteSettings` | **Singleton** — كل نصوص الهيرو، الفيديو، الخريطة، معلومات الاتصال، التذييل. سطر واحد فقط في لوحة التحكم. |
| `HeroStat` | الإحصائيات الثلاث في الهيرو (15 فرعا / +500 تخصصا / +15 سنوات خبرة). |
| `MissionCard` | بطاقات "مهمتنا / رؤيتنا / كفاءاتنا". |
| `CarouselImage` | صور معرض الصور (Carousel) — رفع الصور مباشرة من لوحة التحكم. |
| `Branch` | الفروع المهنية الـ23 (رمز، اسم عربي/فرنسي، لون). |
| `Specialty` | التخصصات (495 تخصصا) المرتبطة بفرع. تُعرض في صفحة الكتالوج. |
| `TrainingSession` | الدورات القادمة (تاريخ، مدة، مقاعد، حالة). |
| `SocialLink` | روابط فيسبوك/لينكدإن/... في التذييل. |
| `InternalApp` | التطبيقات الداخلية (البيداغوجيا، الفوترة، تصنيف التكوينات) — تظهر في شريط التصفح، الهيرو، الشريط، والتذييل حسب الخيارات المفعّلة لكل تطبيق. |
| `NavLink` | روابط "التصفح" في التذييل. |

كل نموذج (عدا `SiteSettings`) قابل للإضافة/الحذف/الترتيب (`order`) من لوحة التحكم
دون لمس الكود.

## الصور (Static → Media)

ضع ملفات الصور الأصلية في `pages/static/pages/images/` (بنفس الأسماء):
`logo-EEMS.png`, `Safety.webp`, `S1.jpg` … `S5.jpg`, `Face.png`, `Link.png`,
`Inst.png`, `Wats.png`, `Twit.png`, `Teleg.png`, `Snap.png`, `head.jpg`.

عند تشغيل `python manage.py seed_data`:

- **تُنسخ إلى MEDIA** (محتوى قابل للتغيير من لوحة التحكم): `logo-EEMS.png` →
  `SiteSettings.logo`، `Safety.webp` → `SiteSettings.hero_image`، و
  `S1.jpg`…`S5.jpg` → 5 سجلات `CarouselImage` (معرض الصور).
- **تبقى في STATIC** (أيقونات ثابتة للموقع): `Face/Link/Inst/Wats/Twit/Teleg/Snap.png`
  تُستخدم كأيقونات حقيقية للروابط الاجتماعية (`SocialLink.static_icon`) بدل
  أيقونات Bootstrap. `head.jpg` غير مستخدم حاليا في أي قالب، متاح لاستخدام مستقبلي.

إن لم يجد الأمر صورة ما يتجاهلها بتحذير (⚠) دون أن يفشل، ولا يعيد نسخ
الشعار/صورة الهيرو إن كانت موجودة مسبقا (لتفادي تكرار الملفات في media عند
إعادة تشغيل seed_data).

## ملاحظة على إصلاح: صفحة الكتالوج لا تعرض البيانات

السبب: `views.nomenclature` كان يبني JSON بـ`json.dumps()` ثم يمرره عبر فلتر
`json_script` الذي يرمّز JSON من جديد بنفسه — أي ترميز مزدوج. الناتج:
`JSON.parse()` في الجافاسكريبت كان يُرجع **سلسلة نصية** بدل **مصفوفة**
(ولهذا ظهر عداد "التخصصات" بطول السلسلة ~35000 بدل 495، والجدول فارغ لأن
`.forEach` غير موجود على string). تم التصحيح بتمرير القائمة Python الخام
(`specialties_data`) وترك `json_script` يتولى الترميز وحده.

## ملاحظات

- الصور (الشعار، صورة الهيرو، صور المعرض) لم تكن متوفرة كملفات في المصدر الثابت
  (روابط `./images/...` فقط) — لذا الحقول من نوع `ImageField` ويمكن رفعها مباشرة
  من لوحة التحكم بعد التشغيل.
- صفحة الكتالوج (`nomenclature.html`) أبقت منطق البحث والتصفية الأصلي بـ JavaScript
  كما هو، لكن البيانات الآن تأتي من قاعدة البيانات (`Specialty`/`Branch`) عبر
  `json_script` بدل مصفوفة JS ثابتة.
- لإعادة تحميل البيانات الأصلية من الصفر: `python manage.py seed_data` (الأمر idempotent،
  يمكن تشغيله أكثر من مرة).
- للإنتاج: غيّر `DEBUG=False`، `SECRET_KEY`، و`ALLOWED_HOSTS` في `settings.py`، وفعّل
  خدمة الملفات الثابتة (`collectstatic`) وملفات الميديا عبر خادم حقيقي (nginx/whitenoise).

---

## الحسابات، السلة، والتسعير حسب الدور (Phase 1–8)

فوق المحتوى الثابت أعلاه، أضاف تطبيقا `accounts` و`enrollment` منظومة زبائن
كاملة مبنية على `django.contrib.auth.User` القياسي (بدون `AUTH_USER_MODEL`
مخصص):

- **التسجيل والتفعيل** — تسجيل عمومي (فرد/مؤسسة) في `/account/register/`
  ينشئ `User(is_active=False)` + `Client(account_status="pending")` وينبّه
  الإدارة بالبريد. إجراء "تفعيل الحساب وإرسال بيانات الدخول" في لوحة
  التحكم يولّد كلمة مرور عشوائية ويرسلها للزبون (لا تُعرض/تُسجَّل في أي
  مكان آخر). الدخول/الخروج/استرجاع كلمة المرور عبر `django.contrib.auth`
  تحت `/account/...`، بقوالب ورسائل بريد بهوية الموقع. اللوحة القديمة
  بالهاتف/الجلسة (`dashboard_login`) أُزيلت لصالح `request.user`.
- **الملف الشخصي والحقول القانونية** — `/mon-espace/profil/` لتعديل بيانات
  الزبون؛ حقول قانونية إضافية للمؤسسات (RC، NIF، NIS، RIB...) مطلوبة فقط
  قبل أن تتمكن مؤسسة VIP من طلب بروفورما.
- **الأسعار حسب الدور** — السعر الأساسي لا يظهر في الـ HTML إطلاقا (وليس
  فقط مخفيا) إلا لزبون VIP مسجَّل الدخول، في كل صفحة يمكن أن يظهر فيها سعر
  (تفصيل التخصص، الكتالوج، السلة، الفواتير).
- **السلة وقائمة الأمنيات** — `Cart`/`CartItem` (زر "أضف إلى السلة" على
  الكتالوج والتفصيل، اختيار مكوّن VIP فقط) و`WishlistItem` ("احفظ لاحقا" +
  "نقل إلى السلة").
- **الدفع حسب الدور** — VIP: "طلب بروفورما" (أساس فوترة + مكوّن لكل سطر +
  رفع بون دي كوماند اختياري) → `ProformaInvoice` مجمَّدة. غير-VIP: "طلب
  عرض سعر" (بدون مكوّن/سعر/مرفق) → `QuoteRequest`، يسعّرها لاحقا محاسب
  سطرا بسطر. كلا المستندين لهما صفحة طباعة HTML عادية (`@media print`،
  بدون أي مكتبة PDF).
- **مجموعة Accountant** — صلاحيات محدودة (عرض/تعديل `ProformaInvoice` و
  `QuoteRequest` فقط) لمراجعة الطلبات وتسعير عروض الأسعار غير-VIP.
- **رسائل بريد** — قوالب مخصصة لكل حدث (تسجيل، تفعيل، طلب بروفورما/عرض
  سعر → إدارة/محاسب، تسعير جاهز → زبون)، مبنية على `emails/base_email.html`.
- **مساحة العميل الموحَّدة** — الملف الشخصي، المشتريات، السلة، قائمة
  الأمنيات، سجل الطلبات، ومقاييس (Chart.js محلي) في `/mon-espace/`.

### بيانات تجريبية

```bash
python manage.py seed_account_groups     # مجموعتا VIP و Normal
python manage.py seed_accountant_group   # مجموعة Accountant
python manage.py seed_demo_users         # 4 زبائن تجريبيون + حساب محاسب (كلمة المرور: Demo2026*)
```

تفاصيل الحسابات التجريبية وسيناريوهات الاختبار اليدوي الكاملة في
[`docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`](docs/TESTING_ACCOUNTS_AND_CHECKOUT.md).
