from django.db import models
from django.conf import settings
from products.models import ProductVariant,Product
# Create your models here.
class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"wishlist of {self.user.first_name} ({self.id})"
    
    
class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="wishlist_items",null=True,blank=True)
    item_added = models.DateTimeField(auto_now_add=True, auto_created=True)
    class Meta:
        unique_together = ('wishlist', 'variant')
