import razorpay
from decimal import Decimal
from django.shortcuts import render, redirect,get_object_or_404,HttpResponse
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

from userFolder.order.models import *
from userFolder.cart.models import *
from userFolder.userprofile.models import *



@require_POST
@login_required(login_url='login')
def create_razorpay_order(request):
    user = request.user

    try:
        cart = Cart.objects.get(user=user)
        if not cart.items.exists():
            return JsonResponse({"success": False, "error": "Cart is empty."}, status=400)
    except Cart.DoesNotExist:
        return JsonResponse({"success": False, "error": "No cart found."}, status=400)

    cart_items = CartItems.objects.filter(cart=cart).select_related('variant')
    variant_ids = [item.variant.id for item in cart_items]

    locked_variants = ProductVariant.objects.filter(id__in=variant_ids)
    variant_map = {variant.id: variant for variant in locked_variants}

    calculated_total_price = 0
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

        calculated_total_price += (current_variant.offer_price * item.quantity)

    # Address from form (same field you already use)
    add_id = request.POST.get('selected_address')
    if not add_id:
        return JsonResponse({"success": False, "error": "Please select a delivery address."}, status=400)

    try:
        address = Address.objects.get(id=add_id, user=user)
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Invalid address selected."}, status=400)

    # Check cart total
    if Decimal(calculated_total_price) != Decimal(cart.total_price):
        cart.total_price = calculated_total_price
        cart.save()
        return JsonResponse(
            {"success": False, "error": "Price mismatch detected. Cart updated. Please review and try again."},
            status=400
        )

    # Create Razorpay order
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    amount_paise = int(calculated_total_price * 100)

    data = {
        "amount": amount_paise,
        "currency": settings.RAZORPAY_CURRENCY,
        "payment_capture": 1,
    }

    # create an order on your system with THIS amount, THIS currency etc .
    razorpay_order = client.order.create(data=data)

    # Save data in session for callback
    request.session['pending_payment'] = {
        'razorpay_order_id': razorpay_order['id'],
        'amount': str(calculated_total_price),
        'address_id': address.id,
    }

    return JsonResponse({
        "success": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
        "amount_display": str(calculated_total_price),
        "currency": settings.RAZORPAY_CURRENCY,
        "user_name": user.first_name,
        "user_email": user.email,
        "user_phone": address.phone_number,
    })

@csrf_exempt
@never_cache
@login_required(login_url='login')
def razorpay_callback(request):
    if request.method != 'POST':
        return redirect('checkout')
    
    user = request.user
    session_data = request.session.get('pending_payment')
    
    if not session_data:
        messages.error(request, "Session expired or invalid payment session.")
        return redirect('checkout')
    
    # Taking data from the session
    razorpay_order_id_session = session_data['razorpay_order_id']
    amount_session = Decimal(session_data['amount'])
    address_id = session_data['address_id']
    
    # Razorpay Sending POST data
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")
    
    '''
        Checking both razorpay post sended id 
        razorpay id in the session is same
    ''' 
    if razorpay_order_id != razorpay_order_id_session:
        messages.error(request, "Payment verification failed (order mismatch).")
        return redirect('checkout')
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    '''
        The signature is a cryptographic hash generated by Razorpay
    '''
    
    #  In here we are verifing the order is from Razorpay 
    try:
        verification_data = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        }
        client.utility.verify_payment_signature(verification_data)
    except razorpay.errors.SignatureVerificationError:
        messages.error(request, "Payment verification failed.")
        return render(request,'orders/order_error.html')
    
    try:
        with transaction.atomic():
            cart = Cart.objects.get(user=user)
            if not cart.items.exists():
                messages.error(request, "Cart is Empty!")
                return redirect('cart')

            cart_items = CartItems.objects.filter(cart=cart).select_related('variant')
            variant_ids = [item.variant.id for item in cart_items]
            locked_variants = ProductVariant.objects.filter(id__in=variant_ids).select_for_update()
            variant_map = {variant.id: variant for variant in locked_variants}

            calculated_total_price = 0
            for item in cart_items:
                current_variant = variant_map.get(item.variant.id)
                if not current_variant:
                    messages.error(request, f"Product {item.variant.product.name} is no longer available.")
                    return redirect('cart')

                if item.quantity > current_variant.stock:
                    messages.error(request, f'Out of stock: {current_variant.product.name}')
                    return redirect('cart')

                calculated_total_price += (current_variant.offer_price * item.quantity)

            # Final safety check: amount from session vs recalculated
            if Decimal(calculated_total_price) != amount_session:
                messages.error(request, 'Price mismatch detected. Payment will be reviewed manually.')
                # Optionally log & create order with status 'pending'
                return redirect('cart')

            address = Address.objects.get(id=address_id, user=user)

            order = OrderMain.objects.create(
                user=user,
                shipping_address_name=address.full_name,
                shipping_address_line_1=address.address_line_1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_pincode=address.postal_code,
                shipping_phone=address.phone_number,
                payment_method='razorpay',
                total_price=calculated_total_price,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                payment_status='paid',
            )

            order_items_to_create = []
            for item in cart_items:
                current_variant = variant_map.get(item.variant.id)

                order_items_to_create.append(
                    OrderItem(
                        order=order,
                        variant=current_variant,
                        product_name=current_variant.product.name,
                        quantity=item.quantity,
                        price_at_purchase=current_variant.offer_price
                    )
                )

                current_variant.stock -= item.quantity
                current_variant.save()

            OrderItem.objects.bulk_create(order_items_to_create)

            cart_items.delete()

            request.session['order_id'] = order.order_id
            # Clear pending payment session
            if 'pending_payment' in request.session:
                del request.session['pending_payment']

            # Send email (same as your COD flow)
            user_email = order.user.email
            plain_message = f'Order placed successfully!'
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
        print(f"Razorpay Order Placement Error: {e}")
        messages.error(request, "Payment received but there was an error creating the order. Support will assist you.")
        # Here you might want to log + notify admin
        return redirect('checkout')

    context = {'order': order}
    return render(request, 'orders/order_success.html', context)