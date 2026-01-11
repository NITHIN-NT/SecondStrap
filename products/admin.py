from django.contrib import admin
from .models import Category,Product,ProductImage,Size,ProductVariant
from .contact_models import ContactModel,Thumbanails
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name','description','is_active']
admin.site.register(Category,CategoryAdmin)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ProductAdminView(admin.ModelAdmin):
    list_display=['name','slug','description','image','category','created_at','is_featured']
    inlines=[ProductImageInline,ProductVariantInline]
admin.site.register(Product,ProductAdminView)

class ProductImageAdminView(admin.ModelAdmin):
    list_display = ['product','image']
admin.site.register(ProductImage,ProductImageAdminView)

class ProductVariantAdminView(admin.ModelAdmin):
    list_display=['product','size','base_price','offer_price','stock']
admin.site.register(ProductVariant,ProductVariantAdminView)

admin.site.register(Size)

class ContactModelAdmin(admin.ModelAdmin):
    list_display = ['name','email','subject','message','is_read','created_at']
admin.site.register(ContactModel,ContactModelAdmin)

class ThumbanailModelAdmin(admin.ModelAdmin):
    list_display = ['image','is_visible']
admin.site.register(Thumbanails,ThumbanailModelAdmin)