from django.contrib import admin
from .models import *
# Register your models here.
class AddressModelAdmin(admin.ModelAdmin):
    list_display =[
        'full_name',
        'address_line_1',
        'address_line_2',
        'city',
        'state',
        'postal_code',
        'phone_number',
        'country',
        'is_default',
        'address_type',
        'user'
    ]
admin.site.register(Address,AddressModelAdmin)