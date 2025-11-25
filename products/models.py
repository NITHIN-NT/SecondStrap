from django.db import models
from django.core.exceptions import ValidationError
from autoslug import AutoSlugField
def product_image_upload_to(instance, filename):
    return f"products/{instance.slug}/{filename}"

class Category(models.Model):
    name = models.CharField(max_length=1024, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=1024)
    slug = AutoSlugField(populate_from='name', unique=True, max_length=1024)
    description = models.TextField()
    image = models.ImageField(upload_to=product_image_upload_to, blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_featured = models.BooleanField(default=False)
    is_selective = models.BooleanField(default=False)
    is_most_demanded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class Size(models.Model):
    size = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.size.upper()

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='variants')
    base_price = models.DecimalField(max_digits=10, decimal_places=2,default=1)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'size')
        indexes = [
            models.Index(fields=['product', 'size'])
        ]

    def __str__(self):
        return f"{self.product.name} - {self.size.size}"

    @property
    def in_stock(self):
        return self.stock > 0

    def clean(self):
        if self.offer_price is not None and self.offer_price >= self.base_price:
            raise ValidationError("Offer price must be less than base price.")