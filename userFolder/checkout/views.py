from django.shortcuts import render, redirect
from userFolder.userprofile.models import *
from userFolder.cart.models import *
from django.views.generic import View
from django.contrib import messages
from decimal import Decimal
from userFolder.wallet.models import Wallet
from userFolder.cart.utils import get_annotated_cart_items
from userFolder.order.models import OrderMain
from django.utils import timezone

class CheckOutView(View):
    def get(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return redirect('cart')

        cart_items = get_annotated_cart_items(user=request.user)
        
        if not cart_items.exists():
            return redirect("products_page_user")
        
        # Stock validation
        if cart_items.exists():
            for item in cart_items:
                if int(item.variant.stock) <= 0 or item.quantity > item.variant.stock:
                    messages.error(request, "Remove the out-of-stock product from the cart to proceed")
                    return redirect("cart")
        else:
            return redirect("products_page_user")
        
        addresses = Address.objects.filter(user=request.user)
        
        # Calculate base totals
        total_price = sum(item.subtotal for item in cart_items)
        cart_total_price = sum(item.product_total for item in cart_items)
        discount = sum(item.actual_discount for item in cart_items)
        shipping = Decimal(30)
        
        grand_total = cart_total_price + shipping
        
        # Check if there's a draft order with wallet deduction applied
        draft_order_id = request.session.get('draft_order_id')
        wallet_applied_amount = Decimal('0')
        
        if draft_order_id:
            try:
                draft_order = OrderMain.objects.get(
                    order_id=draft_order_id,
                    user=request.user,
                    order_status='draft',
                    expires_at__gt=timezone.now()
                )
            
                wallet_applied_amount = draft_order.wallet_deduction
            
                grand_total = draft_order.final_price - wallet_applied_amount
                
            except OrderMain.DoesNotExist:
                if 'draft_order_id' in request.session:
                    del request.session['draft_order_id']
                wallet_applied_amount = Decimal('0')
        
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            wallet = None
        
        grand_total = grand_total.quantize(Decimal('0.01'))
        
        context = {
            "cart_items": cart_items,
            "addresses": addresses,
            'total_price': total_price,
            'cart': cart,
            'discount': discount, 
            'grand_total': grand_total,
            'wallet': wallet,
            'wallet_applied_amount': wallet_applied_amount if wallet_applied_amount > 0 else None,
            'shipping_fee': shipping,
        }
        return render(request, "checkout/checkout.html", context)