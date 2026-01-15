from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from products.models import Product, ProductVariant

class Command(BaseCommand):
    help = 'Updates variant prices based on size increments'

    # Define your price logic here
    # Keys should match the 'size' field in your Size model
    PRICE_INCREMENTS = {
        'XS': Decimal('0.00'),
        'S':  Decimal('20.00'),       # Base price
        'M':  Decimal('50.00'),     # +50
        'L':  Decimal('100.00'),    # +100
        'XL': Decimal('150.00'),    # +150
        'XXL': Decimal('200.00'),   # +200
    }

    def handle(self, *args, **options):
        products = Product.objects.all()
        self.stdout.write(f"Updating variants for {products.count()} products...")

        updated_count = 0

        with transaction.atomic():
            for product in products:
                # Get all variants for this product
                variants = product.variants.all().select_related('size')
                
                # We need a 'reference' price to calculate increments.
                # Usually, S or XS is the base. Let's find the lowest price variant.
                base_variant = variants.order_by('base_price').first()
                if not base_variant:
                    continue
                
                root_price = base_variant.base_price

                for variant in variants:
                    size_name = variant.size.size
                    increment = self.PRICE_INCREMENTS.get(size_name, Decimal('0.00'))

                    if increment > 0:
                        new_base = root_price + increment
                        # Keep your 10% discount logic (0.90) from the previous script
                        new_offer = (new_base * Decimal('0.90')).quantize(Decimal("0.01"))

                        variant.base_price = new_base
                        variant.offer_price = new_offer
                        variant.save()
                        updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} variants.'))