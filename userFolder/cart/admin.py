from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Cart)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart','variant','quantity','size','from_wishlist','item_added']
admin.site.register(CartItems,CartItemAdmin)