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

# models...
from products.models import Category, Product, ProductImage, Size, ProductVariant

ImageFile.LOAD_TRUNCATED_IMAGES = True  # optional

class Command(BaseCommand):
    help = 'Loads products from a JSON file, converts images to WebP, and uploads to Cloudinary'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the JSON file to load.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # configure requests session with retries
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def convert_to_webp(self, image_content):
        try:
            img = Image.open(io.BytesIO(image_content))
            # convert appropriately
            if img.mode in ("CMYK", "P"):
                img = img.convert("RGB")
            # preserve alpha if present
            if "A" in img.getbands():
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=85, method=6)
            buffer.seek(0)
            return ContentFile(buffer.read())
        except UnidentifiedImageError:
            self.stdout.write(self.style.WARNING("    PIL can't identify image file"))
            return None
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error converting image to WebP: {e}"))
            self.stdout.write(self.style.WARNING(traceback.format_exc()))
            return None

    def download_image(self, url):
        try:
            resp = self.session.get(url, timeout=12)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error downloading image {url}: {e}"))
            return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting product import with WebP conversion...'))
        json_file_path = options['json_file']

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found at: {json_file_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Error decoding JSON. Check the file for syntax errors.'))
            return

        total_products = len(products_data)
        skipped_count = 0
        processed_count = 0

        for i, item in enumerate(products_data):
            title = item.get("title", "N/A")
            self.stdout.write(f'Processing {i+1}/{total_products}: {title}')

            # Price parsing
            price_str = item.get('price', None)
            try:
                base_price = Decimal(str(price_str)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError):
                self.stdout.write(self.style.WARNING(f"  Skipping '{title}' - invalid price: {price_str}"))
                skipped_count += 1
                continue

            if base_price <= Decimal("0.00"):
                self.stdout.write(self.style.WARNING(f"  Skipping '{title}' - Zero or missing price."))
                skipped_count += 1
                continue

            offer_price = (base_price * Decimal('0.90')).quantize(Decimal("0.01"))

            # description
            clean_description = strip_tags(item.get('description', ''))

            # category
            category_name = item.get('category')
            if not category_name:
                self.stdout.write(self.style.WARNING(f"  Skipping '{title}' - Missing category."))
                skipped_count += 1
                continue

            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Collection of {category_name}'}
            )

            # handle slug
            handle = item.get('handle')
            if not handle:
                self.stdout.write(self.style.WARNING(f"  Skipping '{title}' - Missing handle/slug."))
                skipped_count += 1
                continue

            # Per-product transaction (so one bad product doesn't rollback everything)
            try:
                with transaction.atomic():
                    product, created = Product.objects.update_or_create(
                        slug=handle,
                        defaults={
                            'name': title,
                            'description': clean_description,
                            'base_price': base_price,
                            'offer_price': offer_price,
                            'alt_text': title,
                            'category': category,
                            'is_featured': random.choice([True, False]),
                            'is_selective': random.choice([True, False]),
                            'is_most_demanded': random.choice([True, False]),
                            'is_active': True,
                        }
                    )

                    images_list = item.get('images', [])
                    if images_list:
                        main_image_url = images_list[0]
                        if not product.image:
                            data = self.download_image(main_image_url)
                            if data:
                                webp_file = self.convert_to_webp(data)
                                if webp_file:
                                    parsed_url = urlparse(main_image_url)
                                    original_name = os.path.basename(parsed_url.path) or 'image'
                                    name_without_ext = os.path.splitext(original_name)[0]
                                    new_filename = f"{name_without_ext}.webp"
                                    product.image.save(new_filename, webp_file, save=True)

                        # gallery
                        ProductImage.objects.filter(product=product).delete()
                        for img_url in images_list:
                            data = self.download_image(img_url)
                            if not data: 
                                continue
                            webp_file = self.convert_to_webp(data)
                            if webp_file:
                                parsed_url = urlparse(img_url)
                                original_name = os.path.basename(parsed_url.path) or 'image'
                                name_without_ext = os.path.splitext(original_name)[0]
                                new_filename = f"{name_without_ext}.webp"
                                p_img = ProductImage(product=product, alt_text=product.name)
                                p_img.image.save(new_filename, webp_file, save=True)

                    # sizes & variants
                    size_variants_list = item.get('size_variants') or ["One Size"]
                    ProductVariant.objects.filter(product=product).delete()
                    for size_name in size_variants_list:
                        size_obj, _ = Size.objects.get_or_create(size=size_name)
                        ProductVariant.objects.create(
                            product=product,
                            size=size_obj,
                            stock=random.randint(10, 50)
                        )

                processed_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error processing product '{title}': {e}"))
                self.stdout.write(self.style.WARNING(traceback.format_exc()))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nImport complete!'))
        self.stdout.write(self.style.SUCCESS(f'Successfully Processed: {processed_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
