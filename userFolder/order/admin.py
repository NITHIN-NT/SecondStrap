from django.contrib import admin
from .models import *
# Register your models here.

class OrderMainModalAdmin(admin.ModelAdmin):
    search_fields = ['order_id']
admin.site.register(OrderMain,OrderMainModalAdmin)
class OrderModalAdmin(admin.ModelAdmin):
    search_fields = ['product_name','is_returned']
    list_display = ['order','variant','product_name','quantity','price_at_purchase','status','is_returned']
admin.site.register(OrderItem,OrderModalAdmin)
admin.site.register(ReturnOrder)
admin.site.register(CancelOrder)
admin.site.register(CancelItem)