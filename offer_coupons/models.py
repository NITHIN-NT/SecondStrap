from django.db import models
from django.utils import timezone
from products.models import Product,Category
from django.core.exceptions import ValidationError
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
    code = models.CharField(max_length=100, unique=True)

    offer_type = models.CharField(max_length=20,choices=OfferType.choices)
    discount_type = models.CharField(max_length=20,choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10,decimal_places=2)

    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    active = models.BooleanField(default=True)

    usage_limit = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def total_used(self):
        return self.usages.filter(is_active=True).count()

    def is_valid_now(self):
        now = timezone.now()
        if not self.active:
            return False
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        if self.usage_limit and self.total_used() >= self.usage_limit:
            return False
        return True

    def clean(self):
        if (
            self.discount_type == DiscountType.PERCENTAGE
            and self.discount_value > 100
        ):
            raise ValidationError("Percentage discount cannot exceed 100")

        if self.offer_type == OfferType.PRODUCT and not self.product:
            raise ValidationError("Product is required for product offer")

        if self.offer_type == OfferType.CATEGORY and not self.category:
            raise ValidationError("Category is required for category offer")

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date")


class OfferUsage(models.Model):
    offer = models.ForeignKey(Offer,on_delete=models.CASCADE,related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    order = models.ForeignKey(OrderMain,on_delete=models.CASCADE)

    discount_amount = models.DecimalField(max_digits=10,decimal_places=2)

    is_active = models.BooleanField(default=False,)

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("offer", "order")

    def __str__(self):
        return f"{self.offer.code} - {self.user}"
