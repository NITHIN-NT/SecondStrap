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
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.http import require_POST,require_http_methods
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from userFolder.order.models import *
from userFolder.cart.models import *
from userFolder.userprofile.models import *
from userFolder.wallet.models import *
from coupon.models import Coupon,CouponUsage
from userFolder.cart.utils import get_annotated_cart_items
from .models import PaymentFailure

from .utils import validate_stock_and_cart,validate_address,calculate_cart_totals,create_draft_order



@require_POST
@login_required(login_url='login')
def apply_coupon(request):
    user = request.user
    coupon_code = request.POST.get('coupon_code', '').strip()
    
    if not coupon_code:
        return JsonResponse({"success": False, "error": "Coupon code not provided"}, status=400)

    cart_items, error = validate_stock_and_cart(user=user)
    if error:
        return JsonResponse(error)  

    # Validate address
    address, error = validate_address(request=request, user=user)
    if error:
        return JsonResponse(error)


    totals = calculate_cart_totals(cart_items)
    
    with transaction.atomic():
        try:
            coupon = Coupon.objects.select_for_update().get(
                code__iexact=coupon_code,
                is_active=True
            )
            
            is_valid, message = coupon.is_valid()
            if not is_valid:
                return JsonResponse({"success": False, "error": message}, status=400)
            
            if totals['grand_total'] < coupon.min_purchase_amount:
                return JsonResponse({
                    "success": False, 
                    "error": f"Minimum purchase of ₹{coupon.min_purchase_amount} required"
                }, status=400)
            
            if coupon.one_time_per_user:
                already_used = CouponUsage.objects.filter(
                    coupon=coupon, 
                    user=user
                ).exists()
                if already_used:
                    return JsonResponse({
                        "success": False, 
                        "error": "You have already used this coupon"
                    }, status=400)
            
            if coupon.coupon_type == 'fixed':
                coupon_discount = min(coupon.coupon_amount, totals['grand_total'])
            elif coupon.coupon_type == 'percentage':
                coupon_discount = (coupon.coupon_percentage / 100) * totals['grand_total']
                coupon_discount = Decimal(coupon_discount)
            else:
                coupon_discount = Decimal('0.00')
            
            
            coupon_discount = min(coupon_discount, totals['grand_total'])
            
            draft_order_id = request.session.get('draft_order_id')
            
            if draft_order_id:
                try:
                    draft_order = OrderMain.objects.select_for_update().get(
                        order_id=draft_order_id,
                        user=user,
                        order_status='draft',
                        expires_at__gt=timezone.now()
                    )
                except OrderMain.DoesNotExist:
                    if 'draft_order_id' in request.session:
                        del request.session['draft_order_id']
                    draft_order = None
            else:
                draft_order = None
            
            if not draft_order:
                draft_order, error = create_draft_order(
                    user=user,
                    address=address,
                    cart_items=cart_items,
                    totals=totals,
                    coupon_code=coupon_code,
                    coupon_discount=coupon_discount,
                )
                if error:
                    return JsonResponse(error, status=500)
                
                request.session['draft_order_id'] = draft_order.order_id
            
            
            final_amount = totals['grand_total'] - coupon_discount - draft_order.wallet_deduction
            final_amount = max(final_amount, Decimal('0.00'))  
            
            draft_order.coupon_code = coupon_code
            draft_order.coupon_discount = coupon_discount
            draft_order.final_price = final_amount
            draft_order.save()
            
            return JsonResponse({
                "success": True,
                "final_amount": str(final_amount),
                "coupon_discount": str(coupon_discount),
                "message": "Coupon applied successfully!",
                "code": coupon_code,
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid coupon code"}, status=400)
        except Exception as e:
            print(f"Coupon application error: {e}")
            return JsonResponse({"success": False, "error": "Failed to apply coupon"}, status=500)


@require_POST
@login_required(login_url='login')
def remove_coupon(request):
    user = request.user
    draft_order_id = request.session.get('draft_order_id')
    
    if not draft_order_id:
        return JsonResponse({"success": False, "error": "No draft order found"}, status=400)

    try:
        with transaction.atomic():
            draft_order = OrderMain.objects.select_for_update().get(
                order_id=draft_order_id,
                user=user,
                order_status='draft',
                expires_at__gte=timezone.now()
            )
            
            final_amount = draft_order.final_price + draft_order.coupon_discount
            
            draft_order.coupon_code = ''
            draft_order.coupon_discount = Decimal('0.00')
            draft_order.final_price = final_amount
            draft_order.save()
            
            return JsonResponse({
                "success": True,
                "final_amount": str(final_amount),
                "message": "Coupon removed successfully!",
            })
            
    except OrderMain.DoesNotExist:
        return JsonResponse({"success": False, "error": "Draft order expired or not found"}, status=400)


@require_POST
@login_required(login_url='login')
def deduct_amount_from_wallet(request):
    user = request.user
    
    cart_items, error = validate_stock_and_cart(user=user)
    if error:
        return error
    
    address, error = validate_address(request=request, user=user)
    if error:
        return error
    
    totals = calculate_cart_totals(cart_items)
    
    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)
            
            if wallet.balance <= 0:
                return JsonResponse({"success": False, "error": "Insufficient wallet balance"}, status=400)
            
            draft_order_id = request.session.get('draft_order_id')
            
            if draft_order_id:
                try:
                    draft_order = OrderMain.objects.select_for_update().get(
                        order_id=draft_order_id,
                        user=user,
                        order_status='draft',
                        expires_at__gt=timezone.now()
                    )
                except OrderMain.DoesNotExist:
                    if 'draft_order_id' in request.session:
                        del request.session['draft_order_id']
                    draft_order = None
            else:
                draft_order = None
            
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
            
            amount_after_coupon = totals['grand_total'] - draft_order.coupon_discount
            wallet_deduction = min(wallet.balance, amount_after_coupon)
            wallet_deduction = max(wallet_deduction, Decimal('0.00'))
            
            final_amount = amount_after_coupon - wallet_deduction
            final_amount = max(final_amount, Decimal('0.00'))
            
            draft_order.wallet_deduction = wallet_deduction
            draft_order.final_price = final_amount
            draft_order.save()
            
            return JsonResponse({
                "success": True,
                "wallet_deduction": str(wallet_deduction),
                "final_amount": str(final_amount),
                "code": draft_order.coupon_code or None,
                "coupon_discount": str(draft_order.coupon_discount),
            })
            
    except Wallet.DoesNotExist:
        return JsonResponse({"success": False, "error": "Wallet not found"}, status=400)
    except Exception as e:
        print(f"Wallet deduction error: {e}")
        return JsonResponse({"success": False, "error": "Failed to process wallet deduction"}, status=500)

@require_POST
@login_required(login_url='login')
def create_razorpay_order(request):
    """
    Creates Razorpay order using draft order (if exists) or cart.
    All amounts come from database - SECURE.
    """
    user = request.user
    draft_order = None
    wallet_deduction = Decimal('0')
    address = None
    
    # Check if draft order exists
    draft_order_id = request.session.get('draft_order_id')
    
    try:
        with transaction.atomic():
            
            if draft_order_id:
                try:
                    # Get draft order with all secure amounts - NOW INSIDE transaction.atomic()
                    draft_order = OrderMain.objects.select_for_update().get(
                        order_id=draft_order_id,
                        user=user,
                        order_status='draft',
                        expires_at__gt=timezone.now()
                    )
                    
                    # Get all amounts from draft order 
                    grand_total = draft_order.final_price
                    wallet_deduction = draft_order.wallet_deduction
                    coupon_deduction = draft_order.coupon_discount
                    amount_to_charge = grand_total 
                    
                    # Get address from draft order
                    address = Address.objects.filter(
                        user=user,
                        full_name=draft_order.shipping_address_name,
                        postal_code=draft_order.shipping_pincode
                    ).first()
                    
                    if not address:
                        # Fallback: get any address if draft address not found
                        address = Address.objects.filter(user=user).first()
                    
                except OrderMain.DoesNotExist:
                    if 'draft_order_id' in request.session:
                        del request.session['draft_order_id']
                    return JsonResponse({"success": False, "error": "Draft order expired."}, status=400)
            else:
                # No draft order - calculate from cart
                cart_items,error = validate_stock_and_cart(user=user)
                if error:
                    return error
                totals = calculate_cart_totals(cart_items=cart_items)
                # Get address from form
                add_id = request.POST.get('selected_address')
                if not add_id:
                    return JsonResponse({"success": False, "error": "Please select a delivery address."}, status=400)
                
                try:
                    address = Address.objects.get(id=add_id, user=user)
                except Address.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Invalid address selected."}, status=400)

                cart_total_price = totals['cart_total_price']
                shipping = totals['shipping']
                grand_total = totals['grand_total']
                amount_to_charge = grand_total
            
            # Validate minimum amount
            if amount_to_charge < Decimal('1'):
                return JsonResponse({"success": False, "error": "Amount too low."}, status=400)
    
    except Exception as e:
        print(f"Transaction error: {e}")
        return JsonResponse({"success": False, "error": "Error processing order."}, status=500)
    
    # Create Razorpay order OUTSIDE the database transaction
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_paise = int(amount_to_charge * 100)

        data = {
            "amount": amount_paise,
            "currency": settings.RAZORPAY_CURRENCY,
            "payment_capture": 1,
        }

        razorpay_order = client.order.create(data=data)
        
    except Exception as e:
        print(f"Razorpay order creation failed: {e}")
        return JsonResponse(
            {"success": False, "error": "Failed to create payment order. Please try again."},
            status=500
        )

    request.session['pending_razorpay'] = {
        'razorpay_order_id': razorpay_order['id'],
        'draft_order_id': draft_order.order_id if draft_order else None,
        'address_id': address.id if address else None,
    }

    return JsonResponse({
        "success": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
        "amount_display": str(amount_to_charge),
        "currency": settings.RAZORPAY_CURRENCY,
        "user_name": user.first_name or user.username,
        "user_email": user.email,
        "user_phone": address.phone_number if address else '',
    })


@csrf_exempt
@never_cache
@login_required(login_url='login')
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
    
        if not session_data:
            messages.error(request, "Session expired or invalid payment session.")
            return render(request, 'orders/order_error.html')
        
        # Get Razorpay response data
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")
        
        # Verify order ID matches
        if razorpay_order_id != session_data['razorpay_order_id']:
            messages.error(request, "Payment verification failed (order mismatch).")
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
        
        # Initialize order variable
        order = None
        
        # Process order
        try:
            with transaction.atomic():
                draft_order_id = session_data.get('draft_order_id')
                
                if draft_order_id:
                    '''
                        DRAFT ORDER FLOW 
                    '''
                    try:
                        draft_order = OrderMain.objects.select_for_update().get(
                            order_id=draft_order_id,
                            user=user,
                            order_status='draft'
                        )
                    except OrderMain.DoesNotExist:
                        messages.error(request, "Draft order not found or expired.")
                        return render(request, 'orders/order_error.html')
                    
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
                                transaction_type='debit',
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
                    
                else:
                    '''
                        NORMAL FLOW 
                    '''
                    try:
                        cart = Cart.objects.get(user=user)
                        if not cart.items.exists():
                            messages.error(request, "Cart is empty!")
                            return render(request, 'orders/order_error.html')
                    except Cart.DoesNotExist:
                        messages.error(request, "Cart not found!")
                        return render(request, 'orders/order_error.html')

                    cart_items = get_annotated_cart_items(user=user)
                    
                    # Lock and validate stock
                    variant_ids = [item.variant.id for item in cart_items]
                    locked_variants = ProductVariant.objects.filter(id__in=variant_ids).select_for_update()
                    variant_map = {variant.id: variant for variant in locked_variants}

                    for item in cart_items:
                        current_variant = variant_map.get(item.variant.id)
                        if not current_variant:
                            messages.error(request, f"Product {item.variant.product.name} is no longer available.")
                            return render(request, 'orders/order_error.html')

                        if item.quantity > current_variant.stock:
                            messages.error(request, f'Out of stock: {current_variant.product.name}')
                            return render(request, 'orders/order_error.html')
                    
                    totals = calculate_cart_totals(cart_items=cart_items)
                    
                    if abs(paid_amount - totals['grand_total']) > Decimal('0.01'):
                        messages.error(request, f"Payment amount mismatch. Expected ₹{totals['grand_total']}, got ₹{paid_amount}")
                        return render(request, 'orders/order_error.html')
                    
                    # Get address
                    address_id = session_data.get('address_id')
                    if not address_id:
                        messages.error(request, "Address information missing.")
                        return render(request, 'orders/order_error.html')
                    
                    try:
                        address = Address.objects.get(id=address_id, user=user)
                    except Address.DoesNotExist:
                        messages.error(request, "Invalid address.")
                        return render(request, 'orders/order_error.html')

                    # Create order
                    order = OrderMain.objects.create(
                        user=user,
                        shipping_address_name=address.full_name,
                        shipping_address_line_1=address.address_line_1,
                        shipping_city=address.city,
                        shipping_state=address.state,
                        shipping_pincode=address.postal_code,
                        shipping_phone=address.phone_number,
                        payment_method='razorpay',
                        payment_status='paid',
                        is_paid=True,
                        order_status='pending',
                        total_price=totals['subtotal'],
                        discount_amount=totals['cart_discount'],
                        shipping_amount=totals['shipping'],
                        wallet_deduction=Decimal('0'),  # No wallet used
                        final_price=totals['grand_total'],
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        razorpay_signature=razorpay_signature,
                    )

                    # Create order items and update stock
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
                    
                    # Clear cart
                    cart_items.delete()
                # Store order ID and clear session data
                request.session['order_id'] = order.order_id
                if 'pending_razorpay' in request.session:
                    del request.session['pending_razorpay']
                if 'draft_order_id' in request.session:
                    del request.session['draft_order_id']

            # Send confirmation email
            try:
                user_email = order.user.email
                plain_message = 'Order placed successfully!'
                html_message = render_to_string(
                    'email/order_success_mail.html',
                    {'order': order, 'items': order.items.all()}
                )
                msg = EmailMultiAlternatives(
                    body=plain_message,
                    subject='Order Successful',
                    to=[user_email],
                )
                msg.attach_alternative(html_message, 'text/html')
                msg.send()
            except Exception as e:
                print(f"Email sending failed: {e}")

            return render(request, 'orders/order_success.html', {'order': order})
            
        except Exception as e:
            print(f"Razorpay Order Placement Error: {e}")
            import traceback
            traceback.print_exc()
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
    return render(request,'orders/order_error.html')