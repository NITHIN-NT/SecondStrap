from django.db import models
from products.models import ProductVariant
from accounts.models import CustomUser
from django.utils import timezone
import random
import string
from decimal import Decimal
from django.db.models import Sum
from datetime import timedelta

ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('shipped', 'Shipped'),
    ('out_for_delivery', 'Out for delivery'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('returned', 'Returned'),
    ('return_requested', 'Return Requested'),
    ('partially_cancelled', 'Partially cancelled'), 
    ('return_canceled','Return Canceled'),
]

PAYMENT_CHOICES = [
    ('cod', 'Cash on Delivery'),
    ('razorpay', 'Razorpay'),
    ('wallet', 'Wallet'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
]

RETURN_CHOICES = [
    ('pending', 'Pending'),
    ('return_requested', 'Return Requested'),
    ('return_approved', 'Return Approved'),
    ('return_rejected', 'Return Rejected'),
    ('return_canceled','Return Canceled'),
]

def generate_order_id():
    date = timezone.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date}-{suffix}"

def generate_return_id():
    suffix = ''.join(random.choices(string.digits,k=8))
    return f"RET-{suffix}"
    
class OrderMain(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='orders')
    order_id = models.CharField(max_length=50, unique=True, default=generate_order_id, editable=False)

    shipping_address_name = models.CharField(max_length=100) 
    shipping_address_line_1 = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)
    shipping_phone = models.CharField(max_length=15)

    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, blank=True, null=True)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=150, null=True, blank=True)
    
    order_status = models.CharField(max_length=150, choices=ORDER_STATUS_CHOICES, default='pending')
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    shipping_amount = models.DecimalField(max_digits=10,decimal_places=2,default=49)
    tax_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    coupon_code = models.CharField(max_length=50, null=True, blank=True)
    
    is_returned = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_progress_status(self):
        status_map = {
            'pending': 0,             
            'confirmed': 1,           
            'shipped': 2,             
            'out_for_delivery': 3,    
            'delivered': 4,           
            'cancelled': -1,
            'returned': -2,
            'return_requested': -2,
            'partially_cancelled': -1,
        }
        return status_map.get(self.order_status, 0)
    
    @property
    def has_return_requested(self):
        return self.order_status == 'return_requested' or self.items.filter(status = 'return_requested').exists()
    
    # using the @ property we can directly call teh has_return_requested in views/shell . 
    # if don't use that we call like has_return_requested() like this 
    class Meta:
        ordering = ['-created_at'] 

    def save(self, *args, **kwargs):
        total = self.total_price or Decimal('0.00')
        discount = self.discount_amount or Decimal('0.00')
        shipping = self.shipping_amount or Decimal('0.00')
        tax = self.tax_amount or Decimal('0.00')
        
        self.final_price = (total + tax + shipping) - discount
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.order_id}"
    
    @property
    def get_total_item_count(self):
        result = self.items.aggregate(total=Sum('quantity'))['total']
        return result or 0
    
    @property
    def get_status_color(self):
        if self.order_status in ['delivered']:
            return 'success' 
        elif self.order_status in ['cancelled', 'returned']:
            return 'danger'  
        elif self.order_status in ['pending', 'return_requested']:
            return 'warning' 
        elif self.order_status in ['confirmed', 'shipped', 'out_for_delivery']:
            return 'primary' 
        return 'secondary'
    
    def is_return_priod_expired(self):
        if self.order_status == 'delivered' and self.updated_at:
            return timezone.now() > (self.updated_at + timedelta(days=7))
        return False
class OrderItem(models.Model):
    order = models.ForeignKey(OrderMain, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    
    product_name = models.CharField(max_length=255) 
    quantity = models.PositiveSmallIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) 
    
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='pending')
    
    is_returned = models.BooleanField(default=False)

    
    @property
    def get_total_price(self):
        return self.price_at_purchase * self.quantity
    
    def __str__(self):
        return f"{self.product_name} ({self.quantity})"
    
    @property
    def get_status_color(self):
        if self.status in ['delivered']:
            return 'success' 
        elif self.status in ['cancelled', 'returned']:
            return 'danger'  
        elif self.status in ['pending', 'return_requested']:
            return 'warning' 
        elif self.status in ['confirmed', 'shipped', 'out_for_delivery']:
            return 'primary' 
        return 'secondary'
class ReturnOrder(models.Model):
    order = models.ForeignKey(OrderMain, on_delete=models.CASCADE  ,related_name='returns')
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='returns')
    
    item = models.ForeignKey(OrderItem,on_delete=models.CASCADE,null=True,blank=True,related_name='return_item')
    return_id = models.CharField(max_length=50, unique=True, default=generate_return_id, editable=False)
    return_reason = models.TextField()
    return_status = models.CharField(max_length=50,choices=RETURN_CHOICES,default='pending')
    return_note = models.TextField(null=True,blank=True)
    return_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.return_id} - {self.user.first_name}"