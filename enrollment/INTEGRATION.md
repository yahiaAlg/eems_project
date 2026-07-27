# دمج تطبيق `enrollment` في المشروع

## 1. انسخ المجلد
انسخ مجلد `enrollment/` بأكمله إلى جذر المشروع (بجانب `pages/`).

## 2. تثبيت المتطلبات
```bash
pip install djangorestframework
```
أضف في `requirements.txt`:
```
djangorestframework>=3.15
```

## 3. `eems_project/settings.py`
```python
INSTALLED_APPS = [
    ...
    "django.contrib.staticfiles",
    "rest_framework",        # <-- أضف هذا
    "pages",
    "enrollment",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAdminUser",   # افتراضيا: كل شيء محمي إلا ما صُرّح بغير ذلك
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        # أضف TokenAuthentication أو JWT هنا إن كان هناك تطبيق موبايل/واجهة منفصلة الحقا
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "registration": "10/hour",   # حماية نقاط التسجيل العمومية من السبام
    },
}
```

## 4. `eems_project/urls.py`
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("api/", include("enrollment.api_urls")),          # /api/sessions/, /api/offerings/, /api/register/...
    path("api/pages/", include("pages.api_urls")),          # /api/pages/branches/, /api/pages/specialties/...
    path("", include("enrollment.urls")),
    path("", include("pages.urls")),
]
```

### ملفات إضافية يجب نسخها إلى `pages/` الموجود
هذا التسليم يضيف 3 ملفات جديدة إلى تطبيق `pages` الموجود مسبقا (بدون المساس بأي ملف حالي):
```
pages/
├── serializers.py     ← جديد (Branch, Specialty, TrainingSession)
├── api_views.py        ← جديد (BranchViewSet, SpecialtyViewSet, TrainingSessionViewSet)
└── api_urls.py           ← جديد (DefaultRouter)
```

## 5. الترحيل (migrations)
```bash
python manage.py makemigrations enrollment
python manage.py migrate
```
> ملاحظة: هذا الإصدار يستبدل `Subscription` القديم بثلاثية `Client` (فرد/مؤسسة) ←
> `Participant` ← `Enrollment`. إذا كانت قد شُغّلت نسخة سابقة من التطبيق ولديها
> بيانات في `Subscription`، يجب كتابة data migration لنقلها يدويا قبل الحذف
> (خارج نطاق هذا التسليم).

## 6. تعبئة بيانات دورة سبتمبر 2025
```bash
python manage.py seed_enrollment
```

---

## نقاط النهاية (Endpoints)

### أ.0) مدونة الشعب المهنية والدورات القادمة (قراءة فقط، بدون مصادقة) — تطبيق `pages`

هذه النقاط تعرض بيانات المؤسسة الثابتة (الفروع الـ23 ومدونة التخصصات، وأيضا
"الدورات القادمة" المعروضة على الصفحة الرئيسية) — وهي منفصلة عن `offerings`
(العروض المُسعّرة القابلة للتسجيل فيها عبر `enrollment`):

| Method | Endpoint | الوصف |
|---|---|---|
| GET | `/api/pages/branches/` | قائمة الفروع المهنية الـ23 (نشطة فقط) |
| GET | `/api/pages/branches/<code>/` | فرع واحد مع كل تخصصاته متداخلة (مثال: `/api/pages/branches/TAG/`) |
| GET | `/api/pages/specialties/` | كل التخصصات (~495)، فلترة: `?branch=<code>&search=<نص>` |
| GET | `/api/pages/specialties/<code>/` | تخصص واحد (مثال: `/api/pages/specialties/TAG0701/`) |
| GET | `/api/pages/trainings/` | "الدورات القادمة" المعروضة في الصفحة الرئيسية (تعريفية، غير مرتبطة بالتسجيل) |

> ربط الكتالوجين: `OfferingSerializer` في `enrollment` يُرجع الآن أيضا
> `specialty_code` و`branch_code` (عندما يكون العرض مرتبطا بتخصص من المدونة)،
> ما يسمح لواجهة المستخدم بالانتقال من عرض تكوين مُسعّر إلى تعريفه الكامل في
> `/api/pages/specialties/<specialty_code>/`.

### أ) الكتالوج العمومي للدورات والعروض المُسعّرة (قراءة فقط، بدون مصادقة) — تطبيق `enrollment`

| Method | Endpoint | الوصف |
|---|---|---|
| GET | `/api/sessions/` | قائمة الدورات المفتوحة |
| GET | `/api/offerings/` | قائمة التخصصات المعروضة، فلترة عبر `?session=<slug>&branch=<id>&level=<1-5>` |
| GET | `/api/offerings/<code>/` | تفاصيل تخصص واحد (مثال: `/api/offerings/TAG0701/`) |

### ب) التسجيل العمومي (كتابة فقط، بدون مصادقة، مُقيّد بمعدل الطلبات)

| Method | Endpoint | الوصف |
|---|---|---|
| POST | `/api/register/individual/` | فرد يسجل نفسه في تخصص واحد أو أكثر |
| POST | `/api/register/enterprise/` | مؤسسة تسجّل دفعة من موظفيها (مشاركين) دفعة واحدة |

**مثال — فرد:**
```json
POST /api/register/individual/
{
  "full_name": "أحمد بن علي",
  "phone": "0770123456",
  "email": "ahmed@example.com",
  "wilaya": "سطيف",
  "offering_codes": ["TAG0701"]
}
```

**مثال — مؤسسة:**
```json
POST /api/register/enterprise/
{
  "company_name": "شركة النور للنقل",
  "trade_register_number": "19/00-1234567",
  "responsible_name": "كريم بوزيد",
  "responsible_position": "مدير الموارد البشرية",
  "phone": "0661234567",
  "email": "hr@ennour-dz.com",
  "offering_codes": ["CIP01Q", "MME07Q"],
  "participants": [
    {"full_name": "سامي حداد", "phone": "0550111222", "position": "عامل مخزن"},
    {"full_name": "ياسين شريف", "position": "عامل مخزن"}
  ]
}
```
↳ هذا الطلب ينشئ `Client` (مؤسسة) واحد، مشاركَين (`Participant`)، و**4 تسجيلات**
(كل مشارك × كل تخصص من `offering_codes`).

كلا النقطتين تُرجعان تمثيل `Client` الكامل + قائمة `Enrollment` المُنشأة.
كلاهما يتضمن حقل `website` مخفي (honeypot) لرصد الروبوتات.

### ج) إدارة الطاقم (CRUD، تتطلب مستخدم إداري `IsAdminUser`)

| Method | Endpoint | الوصف |
|---|---|---|
| GET/POST | `/api/clients/` | قائمة/إنشاء الزبائن، فلترة: `?client_type=&source=&search=` |
| GET/PUT/PATCH/DELETE | `/api/clients/<id>/` | تفاصيل زبون واحد (مع `participants` و`enrollments` متداخلة) |
| GET/POST | `/api/participants/` | فلترة: `?client=<id>` |
| GET/PUT/PATCH/DELETE | `/api/participants/<id>/` | |
| GET/POST | `/api/enrollments/` | فلترة: `?status=&offering=&session=&client_type=` |
| GET/PUT/PATCH/DELETE | `/api/enrollments/<id>/` | تحديث `status` يسجل `handled_by` تلقائيا للمستخدم الحالي |
| GET | `/api/stats/dashboard/` | JSON مطابق للوحة إحصائيات `/admin/` (لبناء واجهة SPA خارجية عند الحاجة) |

## 7. البريد الإلكتروني (اختياري)
كما في السابق — `signals.py` يرسل تنبيها للإدارة (`ADMINS`) عند كل تسجيل جديد،
ويتجاهل الخطأ بصمت إن لم يُضبط البريد.

## 8. لوحة الإحصائيات (واجهة Django Admin التقليدية)
`/admin/enrollment/enrollment/dashboard/` — تبقى متاحة كما هي (Chart.js)، بجانب
النسخة الخام JSON في `/api/stats/dashboard/` لأي استعمال مستقبلي (تطبيق موبايل، لوحة SPA منفصلة...).

## البنية النهائية
```
enrollment/
├── __init__.py
├── apps.py
├── models.py          (FormationSession, Offering, Client, Participant, Enrollment, EnrollmentNote)
├── forms.py            (IndividualSubscribeForm — نموذج الويب العمومي للأفراد)
├── views.py              (catalog, specialty_detail, subscribe, subscribe_success)
├── urls.py                (الواجهة العمومية HTML: /formations/...)
├── serializers.py          (DRF: كتالوج + إدارة + تسجيل عمومي فرد/مؤسسة)
├── api_views.py             (DRF: ViewSets + CreateAPIView + stats APIView)
├── api_urls.py               (DRF router + مسارات صريحة: /api/...)
├── admin.py                   (Client/Participant/Enrollment admins + لوحة إحصائيات)
├── signals.py                  (تنبيه بريدي عند تسجيل جديد)
├── management/commands/seed_enrollment.py
├── templatetags/enrollment_extras.py
├── migrations/__init__.py
└── templates/
    ├── enrollment/            (catalog, specialty_detail, subscribe, subscribe_success)
    └── admin/enrollment/       (dashboard.html, enrollment_changelist.html)
```
