from django.db import migrations

def update_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    # Use id=1 as specified in SITE_ID = 1 in settings.py
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': 'shop.nithinnt.com',
            'name': 'SecondStrap'
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_rename_is_verfied_customuser_is_verified'),
        ('sites', '0001_initial'), # Ensure the sites app initial migration is done
    ]

    operations = [
        migrations.RunPython(update_site_domain),
    ]
