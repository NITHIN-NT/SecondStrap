from django.db import models
from django.conf import settings
from products.models import ProductVariant
# Create your models here.
class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"wishlist of {self.user.first_name} ({self.id})"
    
    
class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist,on_delete=models.CASCADE,related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="wishlist_items")
    size = models.CharField(max_length=10, blank=True)
    item_added = models.DateTimeField(auto_now_add=True, auto_created=True)
    class Meta:
        unique_together = ('wishlist', 'variant', 'size')
