from django.db import models
from django.utils import timezone
from django.conf import settings
from userFolder.order.models import OrderMain
class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED_AMOUNT = "fixed_amount", "Fixed Amount"


class OfferType(models.TextChoices):
    CATEGORY = "category", "Category Offer"
    PRODUCT = "product", "Product Offer"
    AMOUNT_THRESHOLD = "amount_threshold", "Amount Threshold Offer"

class Offer(models.Model):
    name = models.CharField(max_length=350)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True)

    offer_type = models.CharField(max_length=20,choices=OfferType.choices)
    discount_type = models.CharField(max_length=20,choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10,decimal_places=2)

    products = models.ManyToManyField('products.Product', blank=True,related_name='offers')
    categories = models.ManyToManyField('products.Category', blank=True,related_name='offers')
    min_order_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    active = models.BooleanField(default=True)
    display_home = models.BooleanField(default=False)

    usage_limit = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.code})"

class OfferUsage(models.Model):
    offer = models.ForeignKey(Offer,on_delete=models.PROTECT,related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    order = models.ForeignKey(OrderMain,on_delete=models.CASCADE)

    discount_amount = models.DecimalField(max_digits=10,decimal_places=2)

    status = models.BooleanField(default=False,)

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("offer", "user", "order")

    def __str__(self):
        return f"{self.offer.code} - {self.user}"

    