from django.db import models
from products.models import ProductVariant
from accounts.models import CustomUser
from django.utils import timezone
import random
import string
from decimal import Decimal

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

def generate_order_id():
    date = timezone.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date}-{suffix}"

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
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=12) 
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    coupon_code = models.CharField(max_length=50, null=True, blank=True)
    
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
    
    class Meta:
        ordering = ['-created_at'] 

    def save(self, *args, **kwargs):
        total = self.total_price or Decimal('0.00')
        discount = self.discount_amount or Decimal('0.00')
        tax = Decimal(18)
        shipping =Decimal(49.00)
        self.final_price = (total + tax + shipping )- discount
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.order_id}"
    
    
class OrderItem(models.Model):
    order = models.ForeignKey(OrderMain, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    
    product_name = models.CharField(max_length=255) 
    quantity = models.PositiveSmallIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) 
    
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='pending')
    
    @property
    def get_total_price(self):
        return self.price_at_purchase * self.quantity
    
    def __str__(self):
        return f"{self.product_name} ({self.quantity})"
    