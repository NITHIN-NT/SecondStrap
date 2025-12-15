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

    product = models.ManyToManyField(Product, blank=True,related_name='offers')
    category = models.ManyToManyField(Category, blank=True,related_name='offers')
    min_order_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    
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

    def clean(self):        
        '''
            a basic validation
        '''
        # if discountType is percentange. the percentage can't go more than 100
        if (self.discount_type == DiscountType.PERCENTAGE and self.discount_value > 100):
            raise ValidationError("Percentage discount cannot exceed 100")

        # if offerType is Product based and if there is not products selected then raise and error
        if self.offer_type == OfferType.PRODUCT and not self.product.exists():
            raise ValidationError("At least one product is required")

        # Same here from above
        if self.offer_type == OfferType.CATEGORY and not self.category.exists():
            raise ValidationError("At least one category is required")

        # Same here . but in this admin have to enter the amount which start the deal
        if self.offer_type == OfferType.AMOUNT_THRESHOLD and not self.min_order_amount:
            raise ValidationError("Minimum order amount is required")

        # End data cann't be before the start date is checking here
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
        unique_together = ("offer", "user", "order")

    def __str__(self):
        return f"{self.offer.code} - {self.user}"
