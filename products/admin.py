from django.contrib import admin
from .models import Category,Product,ProductImage,Size
# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name','description','is_active']
admin.site.register(Category,CategoryAdmin)
class ProductImageInline(admin.TabularInline): # or admin.StackedInline
    model = ProductImage
    extra = 1 
class ProductAdminView(admin.ModelAdmin):
    list_display=['name','slug','description','image','base_price','offer_price','category','created_at','is_featured','is_most_demanded','is_selective']
admin.site.register(Product,ProductAdminView,inlines=[ProductImageInline])

class ProductImageAdminView(admin.ModelAdmin):
    list_display = ['product','image']
admin.site.register(ProductImage,ProductImageAdminView)
admin.site.register(Size)