import requests
import os
from urllib.parse import urlparse
from io import BytesIO  # <-- Required for in-memory file handling

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from products.models import Product, ProductImage

# --- Import Pillow ---
try:
    from PIL import Image
except ImportError:
    raise ImportError(
        "Pillow is not installed. Please install it with: pip install Pillow"
    )

class Command(BaseCommand):
    help = 'Downloads images, converts them to WebP, and saves them.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting image download and WebP conversion...'))

        # --- 1. Download Main Product Images ---
        products_to_update = Product.objects.filter(
            image_url__isnull=False, 
            image__in=['', None]
        )
        
        self.stdout.write(f'Found {products_to_update.count()} main product images to download.')
        
        for product in products_to_update:
            url = product.image_url
            if not url:
                continue
                
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                # --- WebP Conversion Logic ---
                # 1. Open the downloaded image with Pillow
                img = Image.open(BytesIO(response.content))

                # 2. Create an in-memory buffer to save the new format
                output_buffer = BytesIO()
                
                # 3. Save the image to the buffer in WebP format
                #    We use quality=85 as a good balance.
                #    Using 'RGBA' mode check for images with transparency (like PNGs)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                img.save(output_buffer, format='WEBP', quality=85)
                
                # 4. Get the raw bytes from the buffer
                webp_content = output_buffer.getvalue()
                # --- End Conversion Logic ---

                # Get the original filename and change its extension
                original_filename = os.path.basename(urlparse(url).path)
                base_filename, _ = os.path.splitext(original_filename)
                webp_filename = f"{base_filename}.webp"
                
                # Save the new WebP content to the ImageField
                product.image.save(
                    webp_filename, 
                    ContentFile(webp_content), 
                    save=True
                )
                
                self.stdout.write(self.style.SUCCESS(f'  Converted and saved main image for: {product.name}'))

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'  Failed to download {url} for {product.name}: {e}'))
            except Exception as e:
                # Catch potential Pillow errors (e.g., corrupt image)
                self.stdout.write(self.style.ERROR(f'  Failed to process/convert image for {product.name}: {e}'))

        # --- 2. Download Gallery (ProductImage) Images ---
       # --- 2. Download Gallery (ProductImage) Images ---
        # Find gallery images that have a URL but no file
        gallery_images_to_update = ProductImage.objects.filter(
            image_url__isnull=False, 
            extra_image__in=['', None]  # <-- CORRECTED: Was 'image'
        )

        self.stdout.write(f'\nFound {gallery_images_to_update.count()} gallery images to download.')

        for p_image in gallery_images_to_update:
            url = p_image.image_url
            if not url:
                continue
            
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                # --- WebP Conversion Logic ---
                img = Image.open(BytesIO(response.content))
                output_buffer = BytesIO()
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                img.save(output_buffer, format='WEBP', quality=85)
                webp_content = output_buffer.getvalue()
                # --- End Conversion Logic ---

                original_filename = os.path.basename(urlparse(url).path)
                base_filename, _ = os.path.splitext(original_filename)
                webp_filename = f"{base_filename}.webp"
                
                # Save the new WebP content
                p_image.extra_image.save(  # <-- CORRECTED: Was 'image.save'
                    webp_filename, 
                    ContentFile(webp_content), 
                    save=True
                )
                
                self.stdout.write(self.style.SUCCESS(f'  Converted and saved gallery image for: {p_image.product.name}'))

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'  Failed to download {url} for {p_image.product.name}: {e}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed to process/convert gallery image for {p_image.product.name}: {e}'))

        self.stdout.write(self.style.SUCCESS('\nImage download and conversion complete!'))