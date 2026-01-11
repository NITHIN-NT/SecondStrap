import json, random, os, io, traceback
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError, ImageFile
import requests
from requests.adapters import HTTPAdapter, Retry

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils.html import strip_tags

# Ensure this matches your app name
from products.models import Category, Product, ProductImage, Size, ProductVariant

ImageFile.LOAD_TRUNCATED_IMAGES = True 

class Command(BaseCommand):
    help = 'Loads products from JSON, converts images to WebP, and saves to the database'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the JSON file to load.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def convert_to_webp(self, image_content):
        try:
            img = Image.open(io.BytesIO(image_content))
            if img.mode in ("CMYK", "P"):
                img = img.convert("RGB")
            
            if "A" in img.getbands():
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=85, method=6)
            buffer.seek(0)
            return ContentFile(buffer.read())
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Conversion error: {e}"))
            return None

    def download_image(self, url):
        try:
            resp = self.session.get(url, timeout=12)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Download error {url}: {e}"))
            return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting product import...'))
        json_file_path = options['json_file']

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'File error: {e}'))
            return

        total_products = len(products_data)
        skipped_count = 0
        processed_count = 0

        for i, item in enumerate(products_data):
            title = item.get("title", "N/A")
            self.stdout.write(f'Processing {i+1}/{total_products}: {title}')

            # --- 1. Price Parsing (Now for Variants) ---
            price_str = item.get('price', None)
            try:
                base_price = Decimal(str(price_str)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError):
                skipped_count += 1
                continue

            if base_price <= Decimal("0.00"):
                skipped_count += 1
                continue

            offer_price = (base_price * Decimal('0.90')).quantize(Decimal("0.01"))

            # --- 2. Category Handling ---
            category_name = item.get('category')
            if not category_name:
                skipped_count += 1
                continue

            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Collection of {category_name}'}
            )

            # --- 3. Product Transaction ---
            try:
                with transaction.atomic():
                    # Product model NO LONGER has base_price/offer_price
                    product, created = Product.objects.update_or_create(
                        slug=item.get('handle'),
                        defaults={
                            'name': title,
                            'description': strip_tags(item.get('description', '')),
                            'alt_text': title,
                            'category': category,
                            'is_featured': random.choice([True, False]),
                            'is_active': True,
                        }
                    )

                    # --- 4. Image Handling (WebP) ---
                    images_list = item.get('images', [])
                    if images_list:
                        # Main Image
                        if not product.image:
                            data = self.download_image(images_list[0])
                            if data:
                                webp_file = self.convert_to_webp(data)
                                if webp_file:
                                    filename = f"{os.path.splitext(os.path.basename(urlparse(images_list[0]).path))[0]}.webp"
                                    product.image.save(filename, webp_file, save=True)

                        # Gallery
                        ProductImage.objects.filter(product=product).delete()
                        for img_url in images_list:
                            data = self.download_image(img_url)
                            if data:
                                webp_file = self.convert_to_webp(data)
                                if webp_file:
                                    filename = f"{os.path.splitext(os.path.basename(urlparse(img_url).path))[0]}.webp"
                                    p_img = ProductImage(product=product, alt_text=product.name)
                                    p_img.image.save(filename, webp_file, save=True)

                    # --- 5. Variant & Price Handling ---
                    size_variants_list = item.get('size_variants') or ["One Size"]
                    ProductVariant.objects.filter(product=product).delete()
                    for size_name in size_variants_list:
                        size_obj, _ = Size.objects.get_or_create(size=size_name)
                        ProductVariant.objects.create(
                            product=product,
                            size=size_obj,
                            base_price=base_price,
                            offer_price=offer_price,
                            stock=random.randint(10, 50)
                        )

                processed_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error on '{title}': {e}"))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'Done! Processed: {processed_count}, Skipped: {skipped_count}'))