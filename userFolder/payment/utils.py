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

def validate_stock_and_cart(user):
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