from django.core.management.base import BaseCommand
from django.utils.html import strip_tags
import html

# Replace 'products' with the name of your app
from products.models import Product

class Command(BaseCommand):
    help = 'Removes HTML tags (like <p>, <span>) from product descriptions'

    def handle(self, *args, **options):
        self.stdout.write("Starting description cleanup...")
        
        products = Product.objects.all()
        updated_count = 0
        
        for product in products:
            original_description = product.description
            
            if not original_description:
                continue

            # 1. Strip HTML tags (removes <p>, </div>, <span>, <br>, etc.)
            cleaned_description = strip_tags(original_description)
            
            # 2. Unescape HTML entities (converts &amp; to &, &quot; to ", etc.)
            cleaned_description = html.unescape(cleaned_description)
            
            # 3. Clean up extra whitespace (optional but recommended)
            # This removes leading/trailing whitespace
            cleaned_description = cleaned_description.strip()
            
            # Only save if changes were made
            if original_description != cleaned_description:
                product.description = cleaned_description
                product.save()
                updated_count += 1
                self.stdout.write(f"Cleaned: {product.name}")

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated_count} product descriptions.'))