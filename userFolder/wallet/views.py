import json
import razorpay
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.generic import TemplateView
from .models import Wallet,Transaction,TransactionStatus,TransactionType
from userFolder.userprofile.views import SecureUserMixin
from coupon.models import Coupon,CouponUsage
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import transaction
from django.db.models import F

from userFolder.cart.models import Cart
from products.models import ProductVariant
from userFolder.userprofile.models import Address
from userFolder.order.models import OrderItem,OrderMain
from userFolder.cart.utils import get_annotated_cart_items
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from userFolder.payment.utils import *

# Create your views here.
class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "wallet/wallet.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        user_wallet = Wallet.objects.select_related('user').prefetch_related('transactions').get(user=self.request.user)
        context['wallet'] = user_wallet
        return context

@require_POST
@login_required(login_url='login')
def create_wallet_razorpay_order(request):
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        amount = Decimal(str(amount))
        
    except json.JSONDecodeError:
        return JsonResponse({"status":"error","message":"Amount not get here!"})
    
    MIN_AMOUNT = Decimal('100.00')
    if amount < MIN_AMOUNT:
        return JsonResponse({"success": False, "error": f"Amount should be greater than or equal to ₹{MIN_AMOUNT}."})
    
    user =request.user
    
    wallet = get_object_or_404(Wallet,user=user)
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
        amount_paise = int(amount * 100)
        
        data = {
            "amount": amount_paise,
            "currency" : settings.RAZORPAY_CURRENCY,
            "payment_capture" : 1,
        }

        razorpay_order = client.order.create(data=data)
    except Exception as e:
        print(f"Razorpay Order Creation Error: {e}")
        return JsonResponse({"success": False, "error": "Failed to communicate with payment gateway."})
    
    request.session['pending_payment'] ={
        'razorpay_order_id': razorpay_order['id'],
        'amount': str(amount),
        'wallet_id': wallet.id,
    }
    
    return JsonResponse({
        "success": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
        "amount_display": str(amount),
        "currency": settings.RAZORPAY_CURRENCY,
        "user_name":  user.first_name,
        "user_email": user.email,
        "user_phone": getattr(user, 'phone', '9999999999'), 
    })

@csrf_exempt
@never_cache
@login_required(login_url='login')
@require_POST
def wallet_razorpay_callback(request):
    user = request.user
    session_data = request.session.get('pending_payment',None)
    
    if not session_data :
        return JsonResponse({"status":"error","message":"session expired !"})
    
    razorpay_order_id_session = session_data['razorpay_order_id']
    amount_session = Decimal(session_data['amount'])
    wallet_id = session_data['wallet_id']
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST 
    
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")
    
    if razorpay_order_id != razorpay_order_id_session:
        return JsonResponse({"status":"error","message":"Payment verification failed (Order ID mismatch)."})
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status":"error", "message":"Payment verification failed. Invalid signature."})
    
    try:
        with transaction.atomic():
            Wallet.objects.filter(id=wallet_id).update(balance=F('balance')+ amount_session)
            
            wallet = get_object_or_404(Wallet, id=wallet_id)
            
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='CR',
                amount = amount_session,
                description=f"Wallet Top-up via RazorPay.",
                status = "COMP", 
                payment_id=razorpay_payment_id
            )
            
            return JsonResponse({"status":"success","message":"Amount successfully added to the wallet and verified."})            
            request.session.pop('pending_payment', None)

            
    except Exception as e:
        print(f"Razorpay Wallet Update Error: {e}")
        return JsonResponse({"status":"error", "message":"Payment verified, but failed to update wallet balance due to a server error. Please contact support."})

@require_POST
@never_cache
@login_required
def pay_using_wallet(request):
    user = request.user
    draft_order_id = request.session.get('draft_order_id')

    try:
        with transaction.atomic():
            if draft_order_id:
                order = OrderMain.objects.select_for_update().get(
                    order_id=draft_order_id,
                    user=user,
                    order_status='draft'
                )

                cart_items, error = validate_stock_and_cart(user)
                if error:
                    return JsonResponse(error)

                if order.coupon_code:
                    coupon = Coupon.objects.select_for_update().get(code=order.coupon_code)

                    if coupon.one_time_per_user and CouponUsage.objects.filter(user=user, coupon=coupon).exists():
                        raise ValueError("Coupon already used")

                    coupon.times_used += 1
                    coupon.save()

                    CouponUsage.objects.create(
                        coupon=coupon,
                        user=user,
                        order=order,
                        discount_amount=order.coupon_discount,
                        cart_total_before_discount=order.final_price + order.coupon_discount
                    )

                wallet = Wallet.objects.select_for_update().get(user=user)

                if wallet.balance < order.final_price:
                    raise ValueError("Insufficient wallet balance")

                wallet.balance -= order.final_price
                wallet.save()

                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type=TransactionType.DEBIT,
                    amount=order.final_price,
                    description=f'Payment for order {order.order_id}',
                    status=TransactionStatus.COMPLETED,
                    related_order=order
                )
                
                order.order_status = 'pending'
                order.payment_method = 'wallet'
                order.payment_status = 'paid'
                order.is_paid = True
                order.expires_at = None
                order.save()

                cart_items.delete()
                Cart.objects.filter(user=user).delete()

                return render(request, 'orders/order_success.html', {'order': order})

            cart_items, error = validate_stock_and_cart(user)
            if error:
                return JsonResponse(error)

            totals = calculate_cart_totals(cart_items)

            if totals['grand_total'] > 1000:
                raise ValueError("Orders above ₹1000 are allowed only via UPI.")

            address, error = validate_address(request=request, user=user)
            if error:
                return JsonResponse(error)

            order = OrderMain.objects.create(
                user=user,
                shipping_address_name=address.full_name,
                shipping_address_line_1=address.address_line_1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_pincode=address.postal_code,
                shipping_phone=address.phone_number,
                payment_method='wallet',
                order_status='pending',
                payment_status='pending',
                is_paid=False,
                total_price=totals['subtotal'],
                discount_amount=totals['cart_discount'],
                shipping_amount=totals['shipping'],
                final_price=totals['grand_total']
            )

            wallet = Wallet.objects.select_for_update().get(user=user)

            if wallet.balance < order.final_price:
                raise ValueError("Insufficient wallet balance")

            wallet.balance -= order.final_price
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                transaction_type=TransactionType.DEBIT,
                amount=order.final_price,
                description=f'Payment for order {order.order_id}',
                status=TransactionStatus.COMPLETED,
                related_order=order
            )

            variant_ids = [item.variant.id for item in cart_items]
            variants = ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
            variant_map = {v.id: v for v in variants}

            order_items_to_create = []
            variants_to_update = []
            
            for item in cart_items:
                current_variant = variant_map.get(item.variant.id)

                order_items_to_create.append(
                    OrderItem(
                        order=order,
                        variant=current_variant,
                        product_name=current_variant.product.name,
                        quantity=item.quantity,
                        price_at_purchase=item.final_price,
                        status='pending'
                    )
                )

                current_variant.stock -= item.quantity
                variants_to_update.append(current_variant)

            OrderItem.objects.bulk_create(order_items_to_create)
            ProductVariant.objects.bulk_update(variants_to_update, ["stock"])  

            order.is_paid = True
            order.payment_status = 'paid'
            order.save()

            cart_items.delete()
            Cart.objects.filter(user=user).delete()

        try:
            html_message = render_to_string(
                'email/order_success_mail.html',
                {'order': order, 'items': order.items.all()}
            )
            msg = EmailMultiAlternatives(
                subject='Order Successful',
                body='Order placed successfully!',
                to=[order.user.email],
            )
            msg.attach_alternative(html_message, 'text/html')
            msg.send()
        except Exception as e:
            print("Email error:", e)

        return render(request, 'orders/order_success.html', {'order': order})

    except OrderMain.DoesNotExist:
        messages.error(request, "Draft order not found.")
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found.")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        print("Checkout error:", e)
        messages.error(request, "Something went wrong. Please try again.")

    return redirect('checkout')
