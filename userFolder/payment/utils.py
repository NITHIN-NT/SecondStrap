from decimal import Decimal
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from userFolder.cart.models import Cart
from userFolder.cart.utils import get_annotated_cart_items
from products.models import ProductVariant
from userFolder.userprofile.models import Address
from userFolder.order.models import OrderItem,OrderMain
from coupon.models import Coupon

def validate_stock_and_cart(user):
    try:
        cart = Cart.objects.get(user=user)
        if not cart.items.exists():
            return None, {"success": False, "error": "Cart is empty."}
    except Cart.DoesNotExist:
        return None, {"success": False, "error": "No cart found."}
    
    cart_items = get_annotated_cart_items(user=user)
    variant_ids = [item.variant.id for item in cart_items]

    # Validate stock
    locked_variants = ProductVariant.objects.filter(id__in=variant_ids)
    variant_map = {variant.id: variant for variant in locked_variants}

    for item in cart_items:
        current_variant = variant_map.get(item.variant.id)
        if not current_variant:
            return None, {"success": False, "error": f"Product {item.variant.product.name} unavailable."}
        if item.quantity > current_variant.stock:
            return None, {"success": False, "error": f"Out of stock: {current_variant.product.name}"}

    return cart_items, None

def validate_address(request, user):
    add_id = request.POST.get('selected_address')
    if not add_id:
        return None, {"success": False, "error": "Please select a delivery address."}

    try:
        address = Address.objects.get(id=add_id, user=user)
        return address, None
    except Address.DoesNotExist:
        return None, {"success": False, "error": "Invalid address selected."}
    
def calculate_cart_totals(cart_items):
    # Calculate totals
    subtotal = sum(item.subtotal for item in cart_items)
    cart_total_price = sum(item.product_total for item in cart_items)
    cart_discount = sum(item.actual_discount for item in cart_items)
    shipping = Decimal(30)
    grand_total = cart_total_price + shipping

    return {
        'subtotal': subtotal,
        'cart_total_price': cart_total_price,
        'cart_discount': cart_discount,
        'shipping': shipping,
        'grand_total': grand_total
    }

def sync_draft_order(user, draft_order, cart_items, totals):
    """
    Synchronizes an existing draft order with the current cart items and totals.
    Re-calculates coupon and wallet deductions based on fresh cart state.
    """
    with transaction.atomic():
        # Re-calculate coupon discount if applied
        coupon_discount = Decimal('0.00')
        if draft_order.coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=draft_order.coupon_code, is_active=True)
                is_valid, _ = coupon.is_valid()
                
                # Check if coupon is still valid for the new totals
                if is_valid and totals['grand_total'] >= coupon.min_purchase_amount:
                    if coupon.coupon_type == 'fixed':
                        coupon_discount = min(coupon.coupon_amount, totals['grand_total'])
                    elif coupon.coupon_type == 'percentage':
                        coupon_discount = (Decimal(coupon.coupon_percentage) / Decimal('100')) * totals['grand_total']
                    coupon_discount = min(coupon_discount, totals['grand_total'])
                else:
                    # Invalidate coupon if no longer valid
                    draft_order.coupon_code = ''
                    draft_order.coupon_discount = Decimal('0.00')
            except Coupon.DoesNotExist:
                draft_order.coupon_code = ''
                draft_order.coupon_discount = Decimal('0.00')

        # Re-apply wallet deduction
        wallet_deduction = Decimal('0.00')
        if draft_order.wallet_deduction > 0:
            from userFolder.wallet.models import Wallet
            try:
                wallet = Wallet.objects.get(user=user)
                amount_after_coupon = totals['grand_total'] - coupon_discount
                amount_after_coupon = max(amount_after_coupon, Decimal('0.00'))
                
                # Wallet deduction can't exceed balance or amount after coupon
                wallet_deduction = min(wallet.balance, amount_after_coupon, draft_order.wallet_deduction)
                
                # If the previous deduction was higher than what's now possible, cap it
                # Logic: We keep the deduction if possible, otherwise cap at balance/payable
            except Wallet.DoesNotExist:
                wallet_deduction = Decimal('0.00')

        final_amount = totals['grand_total'] - coupon_discount - wallet_deduction
        final_amount = max(final_amount, Decimal('0.00'))

        # Update OrderMain fields
        draft_order.total_price = totals['subtotal']
        draft_order.discount_amount = totals['cart_discount']
        draft_order.shipping_amount = totals['shipping']
        draft_order.coupon_discount = coupon_discount
        draft_order.wallet_deduction = wallet_deduction
        draft_order.final_price = final_amount
        draft_order.save()

        # Update OrderItems
        draft_order.items.all().delete()
        order_items_to_create = []
        for item in cart_items:
            order_items_to_create.append(
                OrderItem(
                    order=draft_order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    quantity=item.quantity,
                    price_at_purchase=item.final_price,
                    status='draft'
                )
            )
        OrderItem.objects.bulk_create(order_items_to_create)

    return draft_order

def create_draft_order(user,address,cart_items,totals,**extra_fields):
    try:
        with transaction.atomic():
            draft_order = OrderMain.objects.filter(
                user=user,
                order_status='draft',
                expires_at__lt=timezone.now()
            )
            draft_order.delete()
            
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
                total_price=totals['subtotal'],
                discount_amount=totals['cart_discount'],
                shipping_amount=totals['shipping'],
                final_price=totals['grand_total'],
                
                # Status fields
                order_status='draft',  
                expires_at=timezone.now() + timedelta(minutes=5),
                
                **extra_fields
            )
            
            order_items_to_create = []
            # Store cart items in OrderItem
            for item in cart_items:
                order_items_to_create.append(
                    OrderItem(
                        order=draft_order,
                        variant=item.variant,
                        product_name=item.variant.product.name,
                        quantity=item.quantity,
                        price_at_purchase=item.final_price
                    )
                )
            OrderItem.objects.bulk_create(order_items_to_create)

            return draft_order,None

    except Exception as e:
        print(f"Draft order creation error: {e}")
        return None, {"success": False, "error": "Failed to create draft order."}