from django.shortcuts import render, redirect
from userFolder.userprofile.models import *
from userFolder.cart.models import *
from django.views.generic import View
from django.contrib import messages
from decimal import Decimal
from userFolder.wallet.models import Wallet
# # Create your views here.
class CheckOutView(View):
    def get(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return redirect('cart')

        cart_items = CartItems.objects.prefetch_related("variant").filter(cart__user=request.user)
        
        if cart_items.exists():
            for item in cart_items:
                if int(item.variant.stock) <= 0 or item.quantity > item.variant.stock:
                    messages.error(request,"Remove the out-of-stock product from the cart to proceed",)
                    return redirect("cart")
        else:
            return redirect("products_page_user")
        
        addressess = Address.objects.filter(user=request.user)
        
        total_price = Decimal(cart.total_price)
        tax = Decimal(18)
        discount = Decimal(12)
        
        grand_total = (total_price+ tax) - discount
        wallet = Wallet.objects.get(user=request.user)
        context = {
            "cart_items" : cart_items,
            "addresses" : addressess,
            'cart' : cart,
            'discount' : discount, 
            'tax' : tax,
            'grand_total' : grand_total,
            'wallet':wallet
        }
        return render(request, "checkout/checkout.html",context)