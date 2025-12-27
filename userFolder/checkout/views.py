from django.shortcuts import render, redirect
from userFolder.userprofile.models import *
from userFolder.cart.models import *
from django.views.generic import View
from django.contrib import messages
from decimal import Decimal
from userFolder.wallet.models import Wallet
from userFolder.cart.utils import get_annotated_cart_items
# # Create your views here.
class CheckOutView(View):
    def get(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return redirect('cart')

        cart_items = get_annotated_cart_items(user=request.user)
        
        if not cart_items.exists():
            return redirect("products_page_user")
        
        if cart_items.exists():
            for item in cart_items:
                if int(item.variant.stock) <= 0 or item.quantity > item.variant.stock:
                    messages.error(request,"Remove the out-of-stock product from the cart to proceed",)
                    return redirect("cart")
        else:
            return redirect("products_page_user")
        
        addressess = Address.objects.filter(user=request.user)
        
        total_price = sum(item.subtotal for item in cart_items)
        discount = sum(item.actual_discount for item in cart_items)
        shipping = Decimal(30)
        tax = Decimal(8)
        tax_rate = tax / 100
        
        subtotal = total_price + shipping
        subtotal_after_discount = subtotal - discount
        grand_total = subtotal_after_discount * (1 + tax_rate)
        
        tax_amount = subtotal - grand_total
        print(tax_amount)

        grand_total = grand_total.quantize(Decimal('0.01'))
        
        wallet = Wallet.objects.get(user=request.user)
        context = {
            "cart_items" : cart_items,
            "addresses" : addressess,
            'total_price' : total_price,
            'cart' : cart,
            'discount' : discount, 
            'tax' : tax,
            'grand_total' : grand_total,
            'wallet':wallet
        }
        return render(request, "checkout/checkout.html",context)