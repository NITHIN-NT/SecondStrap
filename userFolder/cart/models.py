from django.db import models
from accounts.models import CustomUser
from products.models import ProductVariant


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} for {self.user.first_name}"

    # Geting total_price value from this
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    # Geting total_quantity value from this
    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    class Meta:
        verbose_name_plural = "Carts"  # plural in admin


class CartItems(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True)
    from_wishlist = models.BooleanField(default=False)
    item_added = models.DateTimeField(auto_now_add=True, auto_created=True)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    # Price of the Product 
    @property
    def price(self):
        return self.variant.offer_price

    # Finding the subtotal of the product
    @property
    def subtotal(self):
        return self.price * self.quantity
    
    def save(self, *args, **kwargs):
        if self.quantity > self.variant.stock:
            self.quantity = self.variant.stock
        super().save(*args, **kwargs)  # Call the real save() method

    class Meta:
        verbose_name_plural = "Cart Items"
        unique_together = ("cart", "variant", "size")
