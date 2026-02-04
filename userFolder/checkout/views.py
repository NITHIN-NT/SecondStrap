from django.shortcuts import render, redirect
from userFolder.userprofile.models import *
from userFolder.cart.models import *
from django.views.generic import View
from django.contrib import messages
from decimal import Decimal
from userFolder.wallet.models import Wallet
from userFolder.cart.utils import get_annotated_cart_items
from userFolder.order.models import OrderMain
from coupon.models import Coupon
from django.utils import timezone
from userFolder.payment.utils import calculate_cart_totals, sync_draft_order
from userFolder.cart.utils import verification_requried
from django.utils.decorators import method_decorator

@method_decorator(verification_requried, name='get')
class CheckOutView(View):
    
    def get(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return redirect('cart')

        cart_items = get_annotated_cart_items(user=request.user)
        
        if not cart_items.exists():
            return redirect("products_page_user")
        
        for item in cart_items:
            if int(item.variant.stock) <= 0 or item.quantity > item.variant.stock:
                messages.error(request, "Remove the out-of-stock product from the cart to proceed")
                return redirect("cart")
        
        addresses = Address.objects.filter(user=request.user)
        
        totals = calculate_cart_totals(cart_items=cart_items)
        
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            wallet = None
        
        try:
            now = timezone.now()
            coupons = Coupon.objects.filter(start_date__lte=now,end_date__gte=now,is_active=True)
        except Coupon.DoesNotExist:
            coupons = None
        
        wallet_applied_amount = Decimal('0')
        coupon_discount = Decimal('0')
        coupon_code = None
        grand_total = totals['grand_total']
        
        draft_order_id = request.session.get('draft_order_id')
        
        if draft_order_id:
            try:
                draft_order = OrderMain.objects.get(
                    order_id=draft_order_id,
                    user=request.user,
                    order_status='draft',
                    expires_at__gt=timezone.now()
                )
                
                draft_order = sync_draft_order(request.user, draft_order, cart_items, totals)
                
                wallet_applied_amount = draft_order.wallet_deduction
                coupon_discount = draft_order.coupon_discount
                coupon_code = draft_order.coupon_code
                grand_total = draft_order.final_price

            except OrderMain.DoesNotExist:
                if 'draft_order_id' in request.session:
                    del request.session['draft_order_id']
        context = {
            'cart': cart,
            'wallet': wallet,
            'coupons': coupons,
            'addresses': addresses,
            'cart_items': cart_items,
            
            'total_price': totals['subtotal'],
            'discount': totals['cart_discount'],
            'cart_total_price': totals['cart_total_price'],
            'shipping_fee': totals['shipping'],
            
            'wallet_applied_amount': wallet_applied_amount if wallet_applied_amount > 0 else None,
            'coupon_discount': coupon_discount if coupon_discount > 0 else None,
            'coupon_code': coupon_code if coupon_code else None,
            
            'grand_total': grand_total,
        }
        return render(request, "checkout/checkout.html", context)