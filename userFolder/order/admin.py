from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(OrderMain)
class OrderMainAdmin(admin.ModelAdmin):
    list_display = ('order_id','user','order_status','payment_method','payment_status','is_paid','final_price','created_at','updated_at','is_returned','coupon_code','wallet_deduction')
    

class OrderModalAdmin(admin.ModelAdmin):
    search_fields = ['product_name','is_returned']
    list_display = ['order','variant','product_name','quantity','price_at_purchase','status','is_returned']
admin.site.register(OrderItem,OrderModalAdmin)
admin.site.register(ReturnOrder)
admin.site.register(CancelOrder)
admin.site.register(CancelItem)