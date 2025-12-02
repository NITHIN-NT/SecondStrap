from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from userFolder.userprofile.models import Address
from userFolder.cart.models import Cart, CartItems
from .models import OrderMain, OrderItem, ProductVariant
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
@login_required(login_url='login')
def order(request):
    if request.method != 'POST':
        return redirect('checkout')

    try:
        
        with transaction.atomic():
            user = request.user
            
            try:
                cart = Cart.objects.get(user=user)
                if not cart.items.exists():
                    messages.error(request, "Cart is Empty!")
                    return redirect('cart')
            except Cart.DoesNotExist:
                messages.info(request, 'No cart Found')
                return redirect('Home_page_user')
            
            cart_items = CartItems.objects.filter(cart=cart).select_related('variant')
            variant_ids = [item.variant.id for item in cart_items]
            
            locked_variants = ProductVariant.objects.filter(id__in=variant_ids).select_for_update()
            variant_map = {v.id: v for v in locked_variants}
            
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
            
            add_id = request.POST.get('selected_address')
            if not add_id:
                messages.error(request, 'Please select a delivery address.')
                return redirect('checkout')

            try:
                address = Address.objects.get(id=add_id, user=user)
            except Address.DoesNotExist:
                messages.error(request, 'Invalid address selected.')
                return redirect('checkout') 

            payment_method = request.POST.get('payment_method')
            if not payment_method:            
                messages.info(request, 'Select a payment method')
                return redirect('checkout')
            
            if payment_method != 'cod':
                messages.warning(request, 'Only COD is available right now!')
                return redirect('checkout')
            

            if Decimal(calculated_total_price) != Decimal(cart.total_price):
                messages.error(request, 'Price mismatch detected. Cart updated.')
                cart.total_price = calculated_total_price
                cart.save()
                return redirect('cart')
            
            order = OrderMain.objects.create(
                user=user,
                shipping_address_name=address.full_name,
                shipping_address_line_1=address.address_line_1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_pincode=address.postal_code,
                shipping_phone=address.phone_number,
                payment_method=payment_method,
                total_price=calculated_total_price,
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
    except ValueError as e:
        messages.error(request, f"Value Error: {str(e)}")
        return redirect('cart')
        
    except Exception as e:
        # Log this error in production!
        print(f"Order Placement Error: {e}")
        messages.error(request, "An error occurred while placing your order. Please try again.")
        return redirect('checkout')

    # Success
    context = {
        'order': order
    }
    return render(request, 'orders/order_success.html', context)

def order_details_view(request,order_id):
    user = request.user
        
    order = get_object_or_404(OrderMain,order_id = order_id ,user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    tax = Decimal(18)
    shipping =Decimal(49.00)
    discount = Decimal(12)
    context = {
        'order' : order,
        'order_items' : order_items,
        'tax' : tax,
        'discount' : discount,
        'shipping' : shipping
    }
    
    return render(request,'orders/order_details.html',context)