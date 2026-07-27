pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py seed_data         # 1) محتوى الموقع الأساسي: الهيرو، الفروع، التخصصات، الدورات...
python manage.py seed_enrollment   # 2) كتالوج تكوينات تجريبي (دورة سبتمبر 2025 — 4 تخصصات)
python manage.py seed_samples      # 3) بيانات الميزات الجديدة: شركاء، خطوات، شهادات، تكوين مميز...
python manage.py collectstatic --noinput
python manage.py check
