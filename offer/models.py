from django.db import models
from django.utils import timezone
from django.conf import settings
from userFolder.order.models import OrderMain
from django.core.validators import MinValueValidator,MaxValueValidator

class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"

class OfferType(models.TextChoices):
    CATEGORY = "category", "Category Offer"
    PRODUCT = "product", "Product Offer"

class Offer(models.Model):
    name = models.CharField(max_length=350)
    title = models.TextField(blank=True)

    offer_type = models.CharField(max_length=20,choices=OfferType.choices)
    discount_type = models.CharField(max_length=20,choices=DiscountType.choices)
    discount_percentage = models.DecimalField(max_digits=10,decimal_places=2,default=0)

    products = models.ManyToManyField('products.Product', blank=True,related_name='offers')
    categories = models.ManyToManyField('products.Category', blank=True,related_name='offers')
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True)

    active = models.BooleanField(default=True)
    display_home = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.title})"

class OfferUsage(models.Model):
    offer = models.ForeignKey(Offer,on_delete=models.PROTECT,related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    order = models.ForeignKey(OrderMain,on_delete=models.CASCADE,related_name='offer_used')

    discount_amount = models.DecimalField(max_digits=10,decimal_places=2)

    status = models.BooleanField(default=False,)

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("offer", "user", "order")

    def __str__(self):
        return f"{self.offer.title} - {self.user}"

    