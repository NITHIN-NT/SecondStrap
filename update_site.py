import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SecondStrapProject.settings')
django.setup()

from django.contrib.sites.models import Site

def update_site():
    site_id = 1 # Matches SITE_ID in settings.py
    domain = 'shop.nithinnt.com'
    name = 'SecondStrap'
    
    site, created = Site.objects.get_or_create(id=site_id)
    site.domain = domain
    site.name = name
    site.save()
    
    print(f"Site updated: ID={site.id}, Domain={site.domain}, Name={site.name}")

if __name__ == '__main__':
    update_site()
