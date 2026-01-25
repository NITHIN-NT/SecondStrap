import json, random, os, io, requests
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from PIL import Image, ImageFile

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils.html import strip_tags
from requests.adapters import HTTPAdapter, Retry

# Ensure these match your app name
from products.models import Category, Product, ProductImage, Size, ProductVariant

ImageFile.LOAD_TRUNCATED_IMAGES = True 

class Command(BaseCommand):
    help = 'Imports products from JSON, converts images to WebP, and applies size-based pricing.'

    # ✅ Pricing Logic Configuration (Added ONE SIZE / OS)
    PRICE_INCREMENTS = {
        "ONE SIZE": Decimal("0.00"),

        "XS": Decimal("0.00"),
        "S":  Decimal("20.00"),
        "M":  Decimal("100.00"),
        "L":  Decimal("200.00"),
        "XL": Decimal("350.00"),
        "XXL": Decimal("500.00"),
    }

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def convert_to_webp(self, image_content):
        try:
            img = Image.open(io.BytesIO(image_content))

            if img.mode in ("CMYK", "P"):
                img = img.convert("RGB")

            img = img.convert("RGBA") if "A" in img.getbands() else img.convert("RGB")

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
        json_file_path = options['json_file']
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'File error: {e}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Starting import of {len(products_data)} products...'))
        processed_count = 0
        skipped_count = 0

        for i, item in enumerate(products_data):
            title = item.get("title", "N/A")
            handle = item.get('handle')

            # 1. Base Price Parsing
            try:
                raw_price = Decimal(str(item.get('price'))).quantize(Decimal("0.01"))
                if raw_price <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError):
                self.stdout.write(self.style.WARNING(f" Skipping {title}: Invalid Price"))
                skipped_count += 1
                continue

            # 2. Category Handling
            category_name = item.get('category')
            if not category_name:
                skipped_count += 1
                continue

            category, _ = Category.objects.get_or_create(name=category_name)

            try:
                with transaction.atomic():

                    # 3. Product Creation
                    product, created = Product.objects.update_or_create(
                        slug=handle,
                        defaults={
                            'name': title,
                            'description': strip_tags(item.get('description', '')),
                            'category': category,
                            'is_featured': random.choice([True, False]),
                            'is_active': True,
                        }
                    )

                    # 4. Image Handling
                    images_list = item.get('images', [])

                    if images_list:

                        # Main image
                        if not product.image:
                            data = self.download_image(images_list[0])
                            if data:
                                webp = self.convert_to_webp(data)
                                if webp:
                                    fname = f"{os.path.basename(urlparse(images_list[0]).path).split('.')[0]}.webp"
                                    product.image.save(fname, webp, save=True)

                        # Gallery
                        ProductImage.objects.filter(product=product).delete()

                        for img_url in images_list:
                            img_data = self.download_image(img_url)
                            if img_data:
                                webp_gal = self.convert_to_webp(img_data)
                                if webp_gal:
                                    fname = f"{os.path.basename(urlparse(img_url).path).split('.')[0]}.webp"
                                    ProductImage.objects.create(
                                        product=product,
                                        image=ContentFile(webp_gal.read(), name=fname)
                                    )

                    # ✅ 5. Variants (Supports normal sizes + ONE SIZE)
                    ProductVariant.objects.filter(product=product).delete()

                    one_size = item.get("one_size", False)  # optional boolean from json
                    size_variants_list = item.get("size_variants")

                    # Normalize cases
                    if not size_variants_list:
                        if one_size:
                            size_variants_list = ["ONE SIZE"]
                        else:
                            size_variants_list = ["S"]

                    # If explicitly one_size, override everything
                    if one_size is True:
                        size_variants_list = ["ONE SIZE"]

                    # Clean + normalize
                    size_variants_list = [
                        str(s).strip().upper()
                        for s in size_variants_list
                        if str(s).strip()
                    ]

                    if not size_variants_list:
                        size_variants_list = ["ONE SIZE"]

                    for size_name in size_variants_list:
                        size_obj, _ = Size.objects.get_or_create(size=size_name)

                        increment = self.PRICE_INCREMENTS.get(size_name, Decimal("0.00"))
                        final_base_price = raw_price + increment
                        final_offer_price = (final_base_price * Decimal("0.90")).quantize(Decimal("0.01"))

                        ProductVariant.objects.create(
                            product=product,
                            size=size_obj,
                            base_price=final_base_price,
                            offer_price=final_offer_price,
                            stock=random.randint(10, 50)
                        )

                processed_count += 1
                self.stdout.write(f"✅ Successfully processed {i+1}: {title}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing {title}: {e}"))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Import Complete. Processed: {processed_count}, Skipped: {skipped_count}'
        ))