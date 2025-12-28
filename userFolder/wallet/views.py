import json
import razorpay
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.generic import TemplateView
from .models import Wallet,Transaction,TransactionStatus,TransactionType
from userFolder.userprofile.views import SecureUserMixin
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
@transaction.atomic
def pay_using_wallet(request):

    # CART VALIDATION
    try:
        cart = Cart.objects.select_for_update().get(user=request.user)
        if not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart')
    except Cart.DoesNotExist:
        messages.error(request, "Cart not found.")
        return redirect('Home_page_user')

    cart_items = get_annotated_cart_items(user=request.user)
    variant_ids = [item.variant.id for item in cart_items]

    # Lock product variants
    locked_variants = ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    variant_map = {variant.id: variant for variant in locked_variants}

    # STOCK & PRICE VALIDATION 
    calculated_total_amount = Decimal('0.00')

    for item in cart_items:
        variant = variant_map.get(item.variant.id)

        if not variant:
            messages.error(request,f"{item.variant.product.name} is no longer available.")
            return redirect('cart')

        if item.quantity > variant.stock:
            messages.error(request,f"Out of stock: {variant.product.name}")
            return redirect('cart')

        calculated_total_amount += item.product_total

    # ADDRESS VALIDATION 
    address_id = request.POST.get('selected_address')
    if not address_id:
        messages.error(request, "Please select a delivery address.")
        return redirect('checkout')

    try:
        address = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        messages.error(request, "Invalid address selected.")
        return redirect('checkout')

    # PAYMENT METHOD 
    payment_method = request.POST.get('payment_method')
    if payment_method != 'wallet':
        messages.error(request, "Only wallet payment is supported.")
        return redirect('checkout')

    # WALLET VALIDATION
    try:
        wallet = Wallet.objects.select_for_update().get(user=request.user)
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found.")
        return redirect('checkout')

    if wallet.balance < calculated_total_amount:
        messages.error(request, "Insufficient wallet balance.")
        return redirect('checkout')
    
    subtotal = sum(item.subtotal for item in cart_items)
    cart_total_price = sum(item.product_total for item in cart_items)
    cart_discount = sum(item.actual_discount for item in cart_items)
    shipping = Decimal(30)
    grand_total = cart_total_price + shipping

    # CREATE ORDER 
    order = OrderMain.objects.create(
        user=request.user,
        shipping_address_name=address.full_name,
        shipping_address_line_1=address.address_line_1,
        shipping_city=address.city,
        shipping_state=address.state,
        shipping_pincode=address.postal_code,
        shipping_phone=address.phone_number,
        payment_method=payment_method,
        payment_status='pending',
        total_price=subtotal,
        discount_amount=cart_discount,
        shipping_amount=shipping,
        wallet_deduction=Decimal('0'),
        final_price=grand_total,
    )

    # WALLET DEDUCTION 
    try:
        wallet.balance -= calculated_total_amount
        wallet.save(update_fields=['balance'])

        Transaction.objects.create(
            wallet=wallet,
            transaction_type=TransactionType.DEBIT,
            amount=calculated_total_amount,
            description=f"Order {order.order_id} placed.",
            status=TransactionStatus.COMPLETED,
            related_order=order
        )

    except Exception:
        messages.error(request, "Payment failed. Please try again.")
        raise  # rollback transaction

    # ORDER ITEMS CREATE & STOCK UPDATE 
    order_items = []

    for item in cart_items:
        variant = variant_map[item.variant.id]

        order_items.append(
            OrderItem(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                quantity=item.quantity,
                price_at_purchase=item.final_price
            )
        )

        ProductVariant.objects.filter(
            id=variant.id
        ).update(stock=F('stock') - item.quantity)

    OrderItem.objects.bulk_create(order_items)

    #  MARK ORDER AS PAID 
    order.payment_status = 'paid'
    order.save(update_fields=['payment_status'])

    # CLEAR CART 
    cart_items.delete()

    request.session['order_id'] = order.order_id

    # EMAIL
    try:
        html_message = render_to_string(
            'email/order_success_mail.html',
            {'order': order, 'items': order.items.all()}
        )

        msg = EmailMultiAlternatives(
            subject='Order Successful',
            body='Your order has been placed successfully.',
            to=[order.user.email],
        )
        msg.attach_alternative(html_message, 'text/html')
        msg.send()

    except Exception as e:
        print(f"Order email failed: {e}")

    return render(request, 'orders/order_success.html', {'order': order})

