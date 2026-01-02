from django.contrib import admin
from .models import PaymentFailure
# Register your models here.
@admin.register(PaymentFailure)
class PaymentFailureAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'failure_type', 'error_code', 'amount', 'created_at']
    list_filter = ['failure_type', 'created_at']
    search_fields = ['razorpay_order_id', 'user__username', 'user__email', 'error_message']
