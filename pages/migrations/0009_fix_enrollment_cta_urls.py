from django.db import migrations

OLD_URL = "/formations/"
NEW_URL = "/formations/inscription/"


def fix_urls(apps, schema_editor):
    InternalApp = apps.get_model("pages", "InternalApp")
    NavLink = apps.get_model("pages", "NavLink")

    InternalApp.objects.filter(
        title="التسجيل الإلكتروني", url=OLD_URL,
    ).update(url=NEW_URL)

    NavLink.objects.filter(
        label="سجّل في تكوين", url=OLD_URL,
    ).update(url=NEW_URL)


def revert_urls(apps, schema_editor):
    InternalApp = apps.get_model("pages", "InternalApp")
    NavLink = apps.get_model("pages", "NavLink")

    InternalApp.objects.filter(
        title="التسجيل الإلكتروني", url=NEW_URL,
    ).update(url=OLD_URL)

    NavLink.objects.filter(
        label="سجّل في تكوين", url=NEW_URL,
    ).update(url=OLD_URL)


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0008_sitesettings_epilogue_video_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_urls, revert_urls),
    ]
