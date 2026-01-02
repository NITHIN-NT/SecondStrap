from django.db import models
from django.conf import settings

# Create your models here.

class PaymentFailure(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Transaction info
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Error info
    failure_type = models.CharField(max_length=50)  # PAYMENT_FAILED, MODAL_DISMISSED, etc.
    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # User details
    user_email = models.EmailField(null=True, blank=True)
    user_phone = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.failure_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
