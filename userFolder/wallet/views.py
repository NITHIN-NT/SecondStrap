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
from django.contrib.auth import login as auth_login
from django.db import transaction
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

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

def wallet_top_up_success_view(request):
    """Display wallet top-up success page with the amount added."""
    amount = request.session.pop('wallet_topup_amount', None)
    return render(request, 'wallet/wallet_success.html', {'amount': amount})

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
        
        Transaction.objects.create(
            wallet=wallet,
            transaction_type='CR',
            amount=amount,
            description=f"Wallet Top-up via RazorPay (Pending)",
            status="PD",
            payment_id=razorpay_order['id'] 
        )
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
        "callback_url": request.build_absolute_uri(reverse('wallet_razorpay_callback')),
    })

@csrf_exempt
@never_cache
def wallet_razorpay_callback(request):
    """
    This function handles the callback from Razorpay after a user 
    attempts to add money to their wallet. Uses redirect like checkout.
    """
    if request.method == "GET":
        return redirect('profile_wallet')

    # Razorpay redirect sends form data as POST
    data = request.POST
    
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")
    
    if not razorpay_order_id:
        messages.error(request, "We couldn't find your Razorpay Order ID.")
        return redirect('wallet_top_up_failure')

    # --- STEP 2: Find the Transaction in our Database ---
    transaction_obj = Transaction.objects.filter(
        Q(payment_id=razorpay_order_id) | Q(payment_id=razorpay_payment_id)
    ).first()

    if transaction_obj and transaction_obj.status == TransactionStatus.COMPLETED:
        # Already processed - redirect to success
        messages.success(request, f"Successfully added ₹{transaction_obj.amount} to your wallet!")
        return redirect('wallet_top_up_success')

    # Figure out the amount and wallet to update
    if transaction_obj:
        wallet_id = transaction_obj.wallet.id
        amount_to_add = transaction_obj.amount
    else:
        session_data = request.session.get('pending_payment')
        if session_data and razorpay_order_id == session_data.get('razorpay_order_id'):
            amount_to_add = Decimal(session_data['amount'])
            wallet_id = session_data['wallet_id']
        else:
            messages.error(request, "Transaction session expired. Please try again.")
            return redirect('wallet_top_up_failure')
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        # Mark transaction as failed
        if transaction_obj:
            transaction_obj.status = TransactionStatus.FAILED
            transaction_obj.save()
        messages.error(request, "Security check failed. Invalid signature.")
        return redirect('wallet_top_up_failure')
    except Exception as e:
        print(f"Razorpay verification error: {e}")
        # Mark transaction as failed
        if transaction_obj:
            transaction_obj.status = TransactionStatus.FAILED
            transaction_obj.save()
        messages.error(request, "Something went wrong while verifying the payment.")
        return redirect('wallet_top_up_failure')
    
    # --- STEP 4: Update the Wallet Balance ---
    try:
        with transaction.atomic():
            user_wallet = Wallet.objects.select_for_update().get(id=wallet_id)
            
            if transaction_obj:
                user_wallet.balance += amount_to_add
                user_wallet.save()

                transaction_obj.status = TransactionStatus.COMPLETED
                transaction_obj.payment_id = razorpay_payment_id
                transaction_obj.save()
            else:
                user_wallet.balance += amount_to_add
                user_wallet.save()

                Transaction.objects.create(
                    wallet=user_wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=amount_to_add,
                    description="Wallet Top-up via RazorPay",
                    status=TransactionStatus.COMPLETED, 
                    payment_id=razorpay_payment_id
                )
            
            if 'pending_payment' in request.session:
                request.session.pop('pending_payment', None)
            
            # Store amount in session for success page
            request.session['wallet_topup_amount'] = str(amount_to_add)
            
            # Restore login if session lost due to SameSite cookie (Razorpay redirect)
            if not request.user.is_authenticated:
                auth_login(request, user_wallet.user, backend='django.contrib.auth.backends.ModelBackend')
            
            messages.success(request, f"Successfully added ₹{amount_to_add} to your wallet!")
            return redirect('wallet_top_up_success')
            
    except Exception as e:
        print(f"Error updating wallet: {e}")
        # Mark transaction as failed if wallet update fails
        if transaction_obj:
            transaction_obj.status = TransactionStatus.FAILED
            transaction_obj.save()
        messages.error(request, "Payment was successful, but your balance failed to update. Please contact support.")
        return redirect('wallet_top_up_failure')

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
                    messages.error(request, error.get('error', 'Validation error'))
                    return redirect('checkout')

                # STOCK DEDUCTION FOR DRAFT ORDER (MISSING BEFORE)
                for item in order.items.all():
                    variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                    if item.quantity > variant.stock:
                        messages.error(request, f"Out of stock: {item.product_name}")
                        return redirect('checkout')
                    variant.stock -= item.quantity
                    variant.save()

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
                total_wallet_deduction = order.final_price + order.wallet_deduction

                if wallet.balance < total_wallet_deduction:
                    raise ValueError("Insufficient wallet balance for full payment")

                wallet.balance -= total_wallet_deduction
                wallet.save()

                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type=TransactionType.DEBIT,
                    amount=total_wallet_deduction,
                    description=f'Full wallet payment for order {order.order_id}',
                    status=TransactionStatus.COMPLETED,
                    related_order=order
                )
                
                order.payment_method = 'wallet'
                order.payment_status = 'paid'
                order.is_paid = True
                order.wallet_deduction = total_wallet_deduction
                order.final_price = Decimal('0.00')
                order.order_status = 'pending'
                order.expires_at = None
                order.save()

                # Update item statuses
                order.items.all().update(status='pending')

                cart_items.delete()
                Cart.objects.filter(user=user).delete()

                # Clear draft order from session
                if 'draft_order_id' in request.session:
                    del request.session['draft_order_id']
                # Set order_id in session for authorization
                request.session['order_id'] = order.order_id

            else:
                # Path 2: No direct draft order (though create_draft_order usually handles this)
                cart_items, error = validate_stock_and_cart(user)
                if error:
                    messages.error(request, error.get('error', 'Validation error'))
                    return redirect('checkout')

                totals = calculate_cart_totals(cart_items)

                address, error = validate_address(request=request, user=user)
                if error:
                    messages.error(request, error.get('error', 'Validation error'))
                    return redirect('checkout')

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
                    description=f'Full wallet payment for order {order.order_id}',
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

                # For full wallet payment, we can move the entire final_price to wallet_deduction
                total_paid = order.final_price
                order.wallet_deduction = total_paid
                order.final_price = Decimal('0.00')
                order.is_paid = True
                order.payment_status = 'paid'
                order.save()

                # Delete cart items
                cart_items.delete()
                Cart.objects.filter(user=user).delete()

                # Clear draft order from session
                if 'draft_order_id' in request.session:
                    del request.session['draft_order_id']
                # Set order_id in session for authorization on the animation page
                request.session['order_id'] = order.order_id

        # Send Email (Common Path)
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

        return redirect('order_processing_animation', order_id=order.order_id)

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
