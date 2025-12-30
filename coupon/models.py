from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class CouponType(models.TextChoices):
    FIXED_AMOUNT = 'fixed', 'Fixed Amount'
    PERCENTAGE = 'percentage', 'Percentage'

class Coupon(models.Model):
    name = models.CharField(max_length=150, help_text="Internal name (e.g., 'Summer Sale 2024')")
    code = models.CharField(max_length=50, unique=True, db_index=True, help_text="Code users enter (e.g., 'SUMMER20')")
    description = models.TextField(blank=True, help_text="Internal notes")
    
    coupon_type = models.CharField(max_length=20,choices=CouponType.choices,default=CouponType.FIXED_AMOUNT)
    coupon_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(Decimal('0.01'))],)
    coupon_percentage = models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))])
    min_purchase_amount = models.DecimalField(max_digits=10,decimal_places=2,default=Decimal('0.00'),validators=[MinValueValidator(Decimal('0.00'))],)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    is_active = models.BooleanField(default=True,)

    usage_limit = models.PositiveIntegerField(null=True,blank=True,)
    times_used = models.PositiveIntegerField(default=0,)
    one_time_per_user = models.BooleanField(default=True,)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Coupon'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.coupon_type == CouponType.PERCENTAGE:
            return f"{self.code} - {self.coupon_percentage}% off"
        return f"{self.code} - ₹{self.coupon_amount} off"
    
    @property
    def is_scheduled(self):
        now = timezone.now()
        return self.start_date > now if self.start_date else False
    
    def clean(self):
        errors = {}
        
        if self.coupon_type == CouponType.FIXED_AMOUNT:
            if not self.coupon_amount:
                errors['coupon_amount'] = "Fixed amount is required for 'Fixed Amount' type"
            if self.coupon_percentage:
                errors['coupon_percentage'] = "Remove percentage for 'Fixed Amount' type"
                
        elif self.coupon_type == CouponType.PERCENTAGE:
            if not self.coupon_percentage:
                errors['coupon_percentage'] = "Percentage is required for 'Percentage' type"
            if self.coupon_amount:
                errors['coupon_amount'] = "Remove amount for 'Percentage' type"
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors['end_date'] = "End date must be after start date"
                
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()  
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if coupon is currently valid (date + active status + usage limit)"""
        now = timezone.now()
        
        if not self.is_active:
            return False, "This coupon is currently inactive"
        
        if now < self.start_date:
            return False, f"This coupon is valid from {self.start_date.strftime('%b %d, %Y')}"
        
        if now > self.end_date:
            return False, "This coupon has expired"
        
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "This coupon has reached its usage limit"
        
        return True, "Valid"


class CouponUsage(models.Model):

    from accounts.models import CustomUser
    from userFolder.order.models import OrderMain
    
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey(OrderMain, on_delete=models.CASCADE, related_name='coupon_usage')
    
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    cart_total_before_discount = models.DecimalField(max_digits=10, decimal_places=2)
    
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['coupon', 'order']
    
    def __str__(self):
        return f"{self.user.email} used {self.coupon.code} - ₹{self.discount_amount} off"