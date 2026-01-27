import json
import razorpay
import logging

logger = logging.getLogger(__name__)

from decimal import Decimal
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages 
from django.contrib.auth import login as auth_login
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.http import require_POST,require_http_methods
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from django.urls import reverse
from userFolder.order.models import *
from userFolder.cart.models import *
from userFolder.userprofile.models import *
from userFolder.wallet.models import *
from coupon.models import Coupon,CouponUsage
from userFolder.cart.utils import get_annotated_cart_items
from .models import PaymentFailure

from .utils import validate_stock_and_cart,validate_address,calculate_cart_totals,create_draft_order
from userFolder.order.utils import send_order_success_email


@require_POST
@login_required(login_url='login')
def apply_coupon(request):
    user = request.user
    coupon_code = request.POST.get('coupon_code', '').strip()

    if not coupon_code:
        return JsonResponse({"success": False, "error": "Coupon code not provided"},status=400)

    cart_items, error = validate_stock_and_cart(user=user)
    if error:
        return JsonResponse(error, status=400)

    address, error = validate_address(request=request, user=user)
    if error:
        return JsonResponse(error, status=400)

    totals = calculate_cart_totals(cart_items)

    with transaction.atomic():
        try:
            coupon = Coupon.objects.select_for_update().get(code__iexact=coupon_code,is_active=True)

            is_valid, message = coupon.is_valid()
            if not is_valid:
                return JsonResponse({"success": False, "error": message},status=400)

            if totals['grand_total'] < coupon.min_purchase_amount:
                return JsonResponse({"success": False,
                        "error": f"Minimum purchase of ₹{coupon.min_purchase_amount} required"
                    },status=400)

            if coupon.one_time_per_user and CouponUsage.objects.filter(coupon=coupon,user=user).exists():
                return JsonResponse({"success": False, "error": "You have already used this coupon"},status=400)

            if coupon.coupon_type == 'fixed':
                coupon_discount = min(coupon.coupon_amount,totals['grand_total'])
            elif coupon.coupon_type == 'percentage':
                coupon_discount = (Decimal(coupon.coupon_percentage) / Decimal('100')) * totals['grand_total']
            else:
                coupon_discount = Decimal('0.00')

            coupon_discount = min(coupon_discount,totals['grand_total'])
            draft_order_id = request.session.get('draft_order_id')
            draft_order = None

            if draft_order_id:
                draft_order = OrderMain.objects.filter(
                    order_id=draft_order_id,
                    user=user,
                    order_status='draft',
                    expires_at__gt=timezone.now()
                ).select_for_update().first()

            if draft_order and draft_order.coupon_code:
                return JsonResponse({"success": False, "error": "A coupon is already applied"},status=400)

            if not draft_order:
                draft_order, error = create_draft_order(
                    user=user,
                    address=address,
                    cart_items=cart_items,
                    totals=totals,
                    coupon_code=coupon_code,
                    coupon_discount=coupon_discount
                )
                if error:
                    return JsonResponse(error, status=500)

                request.session['draft_order_id'] = draft_order.order_id

            final_amount = totals['grand_total']- coupon_discount- draft_order.wallet_deduction
            final_amount = max(final_amount, Decimal('0.00'))

            draft_order.coupon_code = coupon_code
            draft_order.coupon_discount = coupon_discount
            draft_order.final_price = final_amount
            draft_order.save()

            return JsonResponse({
                "success": True,
                "message": "Coupon applied successfully",
                "code": coupon_code,
                "coupon_discount": str(coupon_discount),
                "final_amount": str(final_amount)
            })

        except Coupon.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Invalid coupon code"},
                status=400
            )

        except Exception as e:
            print("Coupon error:", e)
            return JsonResponse(
                {"success": False, "error": "Failed to apply coupon"},
                status=500
            )


@require_POST
@login_required(login_url='login')
def remove_coupon(request):
    user = request.user
    draft_order_id = request.session.get('draft_order_id')

    if not draft_order_id:
        return JsonResponse({"success": False, "error": "No draft order found"},status=400)

    try:
        with transaction.atomic():
            draft_order = OrderMain.objects.select_for_update().get(
                order_id=draft_order_id,
                user=user,
                order_status='draft',
                expires_at__gte=timezone.now()
            )

            if not draft_order.coupon_code:
                return JsonResponse({"success": False, "error": "No coupon applied"},status=400)

            final_amount = draft_order.final_price + draft_order.coupon_discount
            final_amount = max(final_amount, Decimal('0.00'))

            draft_order.coupon_code = ''
            draft_order.coupon_discount = Decimal('0.00')
            draft_order.final_price = final_amount
            draft_order.save()

            return JsonResponse({
                "success": True,
                "message": "Coupon removed successfully",
                "final_amount": str(final_amount.quantize(Decimal('0.00')))
            })

    except OrderMain.DoesNotExist:
        return JsonResponse({"success": False, "error": "Session expired or not found"},status=400)
        
@require_POST
@login_required(login_url='login')
def deduct_amount_from_wallet(request):
    user = request.user

    cart_items, error = validate_stock_and_cart(user=user)
    if error:
        return JsonResponse(error, status=400)

    address, error = validate_address(request=request, user=user)
    if error:
        return JsonResponse(error, status=400)

    totals = calculate_cart_totals(cart_items)

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)

            if wallet.balance <= 0:
                return JsonResponse({"success": False, "error": "Insufficient wallet balance"},status=400)

            draft_order_id = request.session.get('draft_order_id')
            draft_order = None

            if draft_order_id:
                draft_order = OrderMain.objects.filter(
                    order_id=draft_order_id,
                    user=user,
                    order_status='draft',
                    expires_at__gt=timezone.now()
                ).select_for_update().first()

            if not draft_order:
                draft_order, error = create_draft_order(
                    user=user,
                    address=address,
                    cart_items=cart_items,
                    totals=totals,
                )
                if error:
                    return JsonResponse(error, status=500)

                request.session['draft_order_id'] = draft_order.order_id

            if draft_order.wallet_deduction > 0:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Wallet balance has already been applied to this order.",
                        "wallet_applied": True,
                        "wallet_deduction": str(draft_order.wallet_deduction),
                        "final_amount": str(draft_order.final_price),
                        },
                    status=400
                    )


            amount_after_coupon = totals['grand_total'] - draft_order.coupon_discount
            amount_after_coupon = max(amount_after_coupon, Decimal('0.00'))

            if amount_after_coupon == 0:
                return JsonResponse({"success": False, "error": "No payable amount left"},status=400)

            wallet_deduction = min(wallet.balance, amount_after_coupon)

            final_amount = amount_after_coupon - wallet_deduction
            final_amount = max(final_amount, Decimal('0.00'))

            draft_order.wallet_deduction = wallet_deduction
            draft_order.final_price = final_amount
            draft_order.save()

            return JsonResponse({
                "success": True,
                "wallet_deduction": str(wallet_deduction),
                "coupon_discount": str(draft_order.coupon_discount),
                "final_amount": str(final_amount),
                "code": draft_order.coupon_code or None,
            })

    except Wallet.DoesNotExist:
        return JsonResponse({"success": False, "error": "Wallet not found"},status=400)

    except Exception as e:
        print("Wallet deduction error:", e)
        return JsonResponse({"success": False, "error": "Failed to process wallet deduction"},status=500)
       

@require_POST
@login_required(login_url='login')
def create_razorpay_order(request):
    """
        Creates Razorpay order using secure DB values only.
    """
    user = request.user
    draft_order = None
    address = None

    draft_order_id = request.session.get('draft_order_id')

    try:
        with transaction.atomic():

            if draft_order_id:
                try:
                    draft_order = OrderMain.objects.select_for_update().get(
                        order_id=draft_order_id,
                        user=user,
                        order_status='draft',
                        expires_at__gt=timezone.now()
                    )
                except OrderMain.DoesNotExist:
                    request.session.pop('draft_order_id', None)
                    return JsonResponse({"success": False, "error": "Draft order expired"},status=400)

                payable_amount = draft_order.final_price

                address = Address.objects.filter(full_name=draft_order.shipping_address_name,postal_code=draft_order.shipping_pincode).first()                  
                
                if not address:
                    address = Address.objects.filter(user=user).first()  
            else:
                cart_items, error = validate_stock_and_cart(user=user)
                if error:
                    return JsonResponse(error, status=400)

                totals = calculate_cart_totals(cart_items)

                add_id = request.POST.get('selected_address')
                if not add_id:
                    return JsonResponse({"success": False, "error": "Please select a delivery address"},status=400)

                try:
                    address = Address.objects.get(id=add_id, user=user)
                except Address.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Invalid address selected"},status=400)
                
                payable_amount = totals['grand_total']

                # Create draft order immediately
                draft_order = OrderMain.objects.create(
                    user=user,
                    shipping_address_name=address.full_name,
                    shipping_address_line_1=address.address_line_1,
                    shipping_city=address.city,
                    shipping_state=address.state,
                    shipping_pincode=address.postal_code,
                    shipping_phone=address.phone_number,
                    payment_method='razorpay',
                    total_price=totals['subtotal'],
                    discount_amount=totals['cart_discount'],
                    shipping_amount=totals['shipping'],
                    final_price=totals['grand_total'],
                    order_status='draft',
                    expires_at=timezone.now() + timedelta(minutes=30)
                )

                # Create draft order items
                for item in cart_items:
                    OrderItem.objects.create(
                        order=draft_order,
                        variant=item.variant,
                        product_name=item.variant.product.name,
                        quantity=item.quantity,
                        price_at_purchase=item.final_price,
                        status='draft'
                    )

            if payable_amount <= Decimal('0.00'):
                return JsonResponse({"success": False, "error": "Invalid payable amount"},status=400)
    except Exception as e:
        print("Order preparation error:", e)
        return JsonResponse(
            {"success": False, "error": "Failed to prepare order"},
            status=500
        )

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_paise = int(payable_amount * 100)
        razorpay_order = client.order.create({
            "amount": amount_paise,
            "currency": settings.RAZORPAY_CURRENCY,
            "payment_capture": 1,
        })
        
        if draft_order:
            draft_order.razorpay_order_id = razorpay_order["id"]
            draft_order.save(update_fields=['razorpay_order_id'])
    except Exception as e:
        print("Razorpay error:", e)
        return JsonResponse(
            {"success": False, "error": "Failed to create payment order"},
            status=500
        )

    request.session['pending_razorpay'] = {
        "razorpay_order_id": razorpay_order["id"],
        "draft_order_id": draft_order.order_id if draft_order else None,
        "address_id": address.id if address else None,
    }

    return JsonResponse({
        "success": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
        "amount_display": str(payable_amount),
        "currency": settings.RAZORPAY_CURRENCY,
        "user_name": user.first_name or user.username,
        "user_email": user.email,
        "user_phone": address.phone_number if address else "",
        "callback_url": settings.RAZORPAY_CALLBACK_URL,
    })


@csrf_exempt
@never_cache
def razorpay_callback(request):
    """
    Converts draft order to final order or creates new order
    All amounts retrieved from database
    """
    session_data = request.session.get('pending_razorpay')
    if request.method == "GET":
        messages.error(request, "Payment failed. Please try again.")
        if session_data and 'pending_razorpay' in request.session:
            del request.session['pending_razorpay']
        return render(request, 'orders/order_error.html')
    
    if request.method == 'POST':
    
        user = request.user
        
        # Get Razorpay response data from POST body
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")
        
        # 1. First try to find order by razorpay_order_id from database (Session Independent)
        try:
            order = OrderMain.objects.get(razorpay_order_id=razorpay_order_id)
            user = order.user
        except OrderMain.DoesNotExist:
            # Fallback: If not in DB, we need the session to find the Draft Order
            if session_data and razorpay_order_id == session_data.get('razorpay_order_id'):
                draft_order_id = session_data.get('draft_order_id')
                try:
                    order = OrderMain.objects.get(order_id=draft_order_id)
                    user = order.user
                except OrderMain.DoesNotExist:
                    messages.error(request, "Order not found.")
                    return render(request, 'orders/order_error.html')
            else:
                # No DB entry and no valid session data
                messages.error(request, "Payment verification failed (session expired or order not found).")
                return render(request, 'orders/order_error.html')
        
        # Verify Razorpay signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            verification_data = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
            client.utility.verify_payment_signature(verification_data)
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, "Payment verification failed. Invalid signature.")
            return render(request, 'orders/order_error.html')
        except Exception as e:
            print(f"Payment verification error: {e}")
            messages.error(request, "Payment verification failed.")
            return render(request, 'orders/order_error.html')
        
        # Verify payment amount from Razorpay
        try:
            payment_details = client.payment.fetch(razorpay_payment_id)
            paid_amount = Decimal(payment_details['amount']) / 100  # Convert paise to rupees
        except Exception as e:
            print(f"Failed to fetch payment details: {e}")
            messages.error(request, "Could not verify payment amount.")
            return render(request, 'orders/order_error.html')
        
        # Process order
        try:
            with transaction.atomic():
                # We already found the 'order' (OrderMain) at the beginning of this function
                # using the razorpay_order_id provided by Razorpay.
                if not order:
                    messages.error(request, "Order not found.")
                    return render(request, 'orders/order_error.html')

                if order.order_status != 'draft':
                    # If it's already processed (e.g., duplicate callback), just show success
                    return redirect('order_processing_animation', order_id=order.order_id)
                
                draft_order = order # For compatibility with existing variable names below

                expected_amount = draft_order.final_price 
                if abs(paid_amount - expected_amount) > Decimal('0.01'):
                    messages.error(request, f"Payment amount mismatch. Expected ₹{expected_amount}, got ₹{paid_amount}")
                    return render(request, 'orders/order_error.html')
                
                # Validate stock using draft order items
                for item in draft_order.items.all():
                    try:
                        variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                    except ProductVariant.DoesNotExist:
                        messages.error(request, f"Product {item.product_name} is no longer available.")
                        return render(request, 'orders/order_error.html')
                    
                    if item.quantity > variant.stock:
                        messages.error(request, f'Out of stock: {item.product_name}')
                        return render(request, 'orders/order_error.html')
                    
                    # Update stock
                    variant.stock -= item.quantity
                    variant.save()
                
                # Deduct wallet balance
                if draft_order.wallet_deduction > 0:
                    try:
                        wallet = Wallet.objects.select_for_update().get(user=user)
                        
                        if wallet.balance < draft_order.wallet_deduction:
                            messages.error(request, "Insufficient wallet balance.")
                            return render(request, 'orders/order_error.html')
                        
                        wallet.balance -= draft_order.wallet_deduction
                        wallet.save()
                        
                        # Create wallet transaction record
                        Transaction.objects.create(
                            wallet=wallet,
                            transaction_type='DB',
                            amount=draft_order.wallet_deduction,
                            description=f'Payment for order {draft_order.order_id}'
                        )
                    except Wallet.DoesNotExist:
                        messages.error(request, "Wallet not found.")
                        return render(request, 'orders/order_error.html')  
                
                # Convert draft to final order
                draft_order.order_status = 'pending'  
                draft_order.payment_method = 'razorpay'
                draft_order.payment_status = 'paid'
                draft_order.is_paid = True
                draft_order.razorpay_order_id = razorpay_order_id
                draft_order.razorpay_payment_id = razorpay_payment_id
                draft_order.razorpay_signature = razorpay_signature
                draft_order.expires_at = None  
                draft_order.save()
                
                order = draft_order
                if order.coupon_code:
                    try:
                        coupon = Coupon.objects.select_for_update().get(code=draft_order.coupon_code)
                        
                        if coupon:
                            coupon.times_used += 1
                            coupon.save()
                            
                            CouponUsage.objects.create(
                                coupon=coupon,
                                user=user,
                                order=order,
                                discount_amount=order.coupon_discount,
                                cart_total_before_discount=order.final_price-order.discount_amount
                            )
                    except Exception as e:
                        return JsonResponse({'success':'False','error':'Something went wrong'})
                    
                # Clear user's cart
                try:
                    cart = Cart.objects.get(user=user)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass
                
                # Update item statuses
                order.items.all().update(status='pending')

            # Store order ID in session as a courtesy (for other parts of site)
            request.session['order_id'] = order.order_id
            if 'pending_razorpay' in request.session:
                del request.session['pending_razorpay']
            if 'draft_order_id' in request.session:
                del request.session['draft_order_id']

            # 🛑 CRITICAL: If session was lost during Razorpay's POST callback (SameSite=Lax issue),
            # we must log the user back in manually so the next redirect works.
            if not request.user.is_authenticated:
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Redirect to animation page (email will be sent there)
            return redirect('order_processing_animation', order_id=order.order_id)

        except Exception as e:
            print(f"Razorpay Order Placement Error: {e}")
            messages.error(request, "Payment received but there was an error creating the order. Our support team will assist you.")
            return render(request, 'orders/order_error.html')

    return redirect('checkout')

@require_http_methods(["POST"])
def payment_failed_log(request):    
    try:
        data = json.loads(request.body)
        
        # Save to database
        PaymentFailure.objects.create(
            user=request.user if request.user.is_authenticated else None,
            razorpay_order_id=data.get('order_id'),
            amount=data.get('amount'),
            failure_type=data.get('failure_type', 'PAYMENT_FAILED'),
            error_code=data.get('error_code'),
            error_message=data.get('error_description'),
            user_email=data.get('user_email'),
            user_phone=data.get('user_phone')
        )

        # Update Order status to 'failed'
        order_id = data.get('order_id')
        if order_id:
            OrderMain.objects.filter(razorpay_order_id=order_id, order_status='draft').update(order_status='failed')
        
        # Also log to file
        logger.error(
            f"Payment Failed - Type: {data.get('failure_type')} | "
            f"Order: {data.get('order_id')} | "
            f"Error: {data.get('error_code')} - {data.get('error_description')}"
        )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Failed to log payment error: {str(e)}")
        return JsonResponse({'success': False}, status=500)
       
@require_http_methods(["GET"])          
def payment_failed_page(request):
    order_id = request.GET.get('order_id')
    context = {
        'order_id': order_id
    }
    return render(request,'orders/order_error.html', context)

@login_required(login_url='login')
def retry_order_payment(request, order_id):
    """
    Re-initiates payment for an order that failed.
    """
    user = request.user
    try:
        order = OrderMain.objects.get(order_id=order_id, user=user, order_status='failed')
    except OrderMain.DoesNotExist:
        messages.error(request, "Order not found or not eligible for retry.")
        return redirect('checkout')

    # Prepare Razorpay order
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_paise = int(order.final_price * 100)
        razorpay_order = client.order.create({
            "amount": amount_paise,
            "currency": settings.RAZORPAY_CURRENCY,
            "payment_capture": 1,
        })
        
        order.razorpay_order_id = razorpay_order["id"]
        order.save(update_fields=['razorpay_order_id'])
        
        # Update session for callback
        request.session['pending_razorpay'] = {
            "razorpay_order_id": razorpay_order["id"],
            "draft_order_id": order.order_id,
        }

        # Handle phone number for prefill
        user_phone = order.shipping_phone or ""

        return JsonResponse({
            "success": True,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "amount_paise": amount_paise,
            "amount_display": str(order.final_price),
            "currency": settings.RAZORPAY_CURRENCY,
            "user_name": user.first_name or user.username,
            "user_email": user.email,
            "user_phone": user_phone,
            "callback_url": settings.RAZORPAY_CALLBACK_URL,
        })
    except Exception as e:
        print("Retry payment error:", e)
        return JsonResponse({"success": False, "error": f"Failed to re-initiate payment: {str(e)}"}, status=500)