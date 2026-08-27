pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py flush

python manage.py seed_data         # 1) محتوى الموقع الأساسي: الهيرو، الفروع، التخصصات، الدورات...
python manage.py seed_enrollment   # 2) كتالوج تكوينات تجريبي (دورة سبتمبر 2025 — 4 تخصصات)
python manage.py seed_samples      # 3) بيانات الميزات الجديدة: شركاء، خطوات، شهادات، تكوين مميز...
python manage.py seed_formateurs         # 4) أسئلة شائعة
python manage.py seed_formateur_profiles # 4.1) شهادات + مسار مهني + نموذج CV مخصص واحد للتجربة
python manage.py seed_gallery         # 4) أسئلة شائعة
python manage.py seed_fiche_technique     # 4.2) حقول الملف التقني + مرفق إضافي + نموذج فيشة مخصصة واحد للتجربة
python manage.py seed_about_faqs         # 4) أسئلة شائعة
python manage.py collectstatic --noinput
python manage.py check
