import razorpay
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages 
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from userFolder.order.models import *
from userFolder.cart.models import *
from userFolder.userprofile.models import *
from userFolder.wallet.models import *

from userFolder.cart.utils import get_annotated_cart_items


@require_POST
@login_required(login_url='login')
def deduct_amount_from_wallet(request):
    """
        Creates a draft order with wallet deduction applied
        Stores all amounts securely in the database
    """
    user = request.user
    
    try:
        cart = Cart.objects.get(user=user)
        if not cart.items.exists():
            return JsonResponse({"success": False, "error": "Cart is empty."}, status=400)
    except Cart.DoesNotExist:
        return JsonResponse({"success": False, "error": "No cart found."}, status=400)
    
    cart_items = get_annotated_cart_items(user=user)
    variant_ids = [item.variant.id for item in cart_items]

    # Validate stock
    locked_variants = ProductVariant.objects.filter(id__in=variant_ids)
    variant_map = {variant.id: variant for variant in locked_variants}

    for item in cart_items:
        current_variant = variant_map.get(item.variant.id)
        if not current_variant:
            return JsonResponse(
                {"success": False, "error": f"Product {item.variant.product.name} is no longer available."},
                status=400
            )
        if item.quantity > current_variant.stock:
            return JsonResponse(
                {"success": False, "error": f"Out of stock: {current_variant.product.name}"},
                status=400
            )

    # Validate address
    add_id = request.POST.get('selected_address')
    if not add_id:
        return JsonResponse({"success": False, "error": "Please select a delivery address."}, status=400)

    try:
        address = Address.objects.get(id=add_id, user=user)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Invalid address selected."}, status=400)
    
    # Calculate totals
    subtotal = sum(item.subtotal for item in cart_items)
    cart_total_price = sum(item.product_total for item in cart_items)
    cart_discount = sum(item.actual_discount for item in cart_items)
    shipping = Decimal(30)
    grand_total = cart_total_price + shipping
    
    # Get wallet and calculate deduction
    try:
        wallet = Wallet.objects.get(user=user)
        wallet_deduction = min(wallet.balance, grand_total)
    except Wallet.DoesNotExist:
        return JsonResponse({"success": False, "error": "Wallet not found."}, status=400)
    
    if wallet_deduction <= 0:
        return JsonResponse({"success": False, "error": "Insufficient wallet balance."}, status=400)
    
    final_amount = grand_total - wallet_deduction

    try:
        with transaction.atomic():
            OrderMain.objects.filter(
                user=user,
                order_status='draft',
                created_at__lt=timezone.now() - timedelta(minutes=30)
            ).delete()
            
            # Create draft order using OrderMain table
            draft_order = OrderMain.objects.create(
                user=user,
                # Address fields
                shipping_address_name=address.full_name,
                shipping_address_line_1=address.address_line_1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_pincode=address.postal_code,
                shipping_phone=address.phone_number,
                
                # Payment fields
                payment_method='pending',  
                payment_status='pending',
                
                # Financial fields - SECURE SOURCE OF TRUTH
                total_price=subtotal,
                discount_amount=cart_discount,
                shipping_amount=shipping,
                wallet_deduction=wallet_deduction,
                final_price=grand_total,
                
                # Status fields
                order_status='draft',  
                expires_at=timezone.now() + timedelta(minutes=30),
            )
            
            # Store cart items in OrderItem
            for item in cart_items:
                OrderItem.objects.create(
                    order=draft_order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    quantity=item.quantity,
                    price_at_purchase=item.final_price
                )
            
            request.session['draft_order_id'] = draft_order.order_id
            
    except Exception as e:
        print(f"Draft order creation error: {e}")
        return JsonResponse({"success": False, "error": "Failed to apply wallet amount."}, status=500)
    
    return JsonResponse({
        "success": True,
        "wallet_deduction": str(wallet_deduction),
        "final_amount": str(final_amount),
    })


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
                    
                    # Get all amounts from draft order (SECURE)
                    grand_total = draft_order.final_price
                    wallet_deduction = draft_order.wallet_deduction
                    amount_to_charge = grand_total - wallet_deduction
                    
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
                try:
                    cart = Cart.objects.get(user=user)
                    if not cart.items.exists():
                        return JsonResponse({"success": False, "error": "Cart is empty."}, status=400)
                except Cart.DoesNotExist:
                    return JsonResponse({"success": False, "error": "No cart found."}, status=400)

                # Get address from form
                add_id = request.POST.get('selected_address')
                if not add_id:
                    return JsonResponse({"success": False, "error": "Please select a delivery address."}, status=400)
                
                try:
                    address = Address.objects.get(id=add_id, user=user)
                except Address.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Invalid address selected."}, status=400)

                cart_items = get_annotated_cart_items(user=user)
                cart_total_price = sum(item.product_total for item in cart_items)
                shipping = Decimal(30)
                grand_total = cart_total_price + shipping
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
    if request.method != 'POST':
        return redirect('checkout')
    
    user = request.user
    session_data = request.session.get('pending_razorpay')
    
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
                    DRAFT ORDER FLOW (With Wallet) 
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
                
                expected_amount = draft_order.final_price - draft_order.wallet_deduction
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
                draft_order.expires_at = None  # Clear expiration
                draft_order.save()
                
                order = draft_order
                
                # Clear user's cart
                try:
                    cart = Cart.objects.get(user=user)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass
                
            else:
                '''
                    NORMAL FLOW (Without Wallet)
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

                # Calculate totals
                subtotal = sum(item.subtotal for item in cart_items)
                cart_total_price = sum(item.product_total for item in cart_items)
                cart_discount = sum(item.actual_discount for item in cart_items)
                shipping = Decimal(30)
                grand_total = cart_total_price + shipping
                
                if abs(paid_amount - grand_total) > Decimal('0.01'):
                    messages.error(request, f"Payment amount mismatch. Expected ₹{grand_total}, got ₹{paid_amount}")
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
                    total_price=subtotal,
                    discount_amount=cart_discount,
                    shipping_amount=shipping,
                    wallet_deduction=Decimal('0'),  # No wallet used
                    final_price=grand_total,
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