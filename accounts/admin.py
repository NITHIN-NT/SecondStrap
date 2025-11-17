from django.contrib import admin
from .models import CustomUser,EmailOTP
# Register your models here.
class CustomUserModelAdmin(admin.ModelAdmin):
    list_display = ['email','first_name','last_name','phone','profile','is_active','is_staff','date_joined']
admin.site.register(CustomUser,CustomUserModelAdmin)
admin.site.register(EmailOTP)