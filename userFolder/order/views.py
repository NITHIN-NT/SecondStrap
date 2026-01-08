import json
from django.shortcuts import render, redirect,get_object_or_404,HttpResponse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required
from userFolder.userprofile.models import Address
from userFolder.cart.models import Cart
from userFolder.wallet.models import *
from django.db.models import F
from .models import *
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .utils import render_to_pdf 
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.cache import never_cache
from userFolder.cart.utils import get_annotated_cart_items

@never_cache
@login_required(login_url='login')
def order(request):
    if request.method != 'POST':
        return redirect('checkout')
    
    if request.session.get('draft_order_id'):
        messages.error(request,'Only UPI applicable')
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
            
            cart_items = get_annotated_cart_items(user=user)
            variant_ids = [item.variant.id for item in cart_items]
            
            locked_variants = ProductVariant.objects.filter(id__in=variant_ids).select_for_update()
            variant_map = {variant.id: variant for variant in locked_variants}
            
            # calculated_total_price = 0
            for item in cart_items:
                current_variant = variant_map.get(item.variant.id)
                
                if not current_variant:
                    messages.error(request, f"Product {item.variant.product.name} is no longer available.")
                    return redirect('cart')

                if item.quantity > current_variant.stock:
                    messages.error(request, f'Out of stock: {current_variant.product.name}')
                    return redirect('cart')

                # calculated_total_price += item.product_total
            
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
            
            subtotal = sum(item.subtotal for item in cart_items)
            cart_total_price = sum(item.product_total for item in cart_items)
            cart_discount = sum(item.actual_discount for item in cart_items)
            shipping = Decimal(30)
            grand_total = cart_total_price + shipping
            
            if grand_total > Decimal('1000'):
                messages.info(request,'Order above 1000 , only UPI')
                return redirect('checkout')
            
            order = OrderMain.objects.create(
                user=user,
                shipping_address_name=address.full_name,
                shipping_address_line_1=address.address_line_1,
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_pincode=address.postal_code,
                shipping_phone=address.phone_number,
                payment_method=payment_method,
                order_status = 'pending',
                total_price=subtotal,
                discount_amount = cart_discount,
                shipping_amount = shipping,
                final_price = grand_total
                
            )
            
            order_items_to_create = []
            variants_to_update = []
            
            for item in cart_items:
                current_variant = variant_map.get(item.variant.id)
                print(current_variant)
                order_items_to_create.append(
                    OrderItem(
                        order=order,
                        variant=current_variant,
                        product_name=current_variant.product.name,
                        quantity=item.quantity,
                        price_at_purchase=item.final_price
                    )
                )
                
                current_variant.stock -= item.quantity
                variants_to_update.append(current_variant)
                                
            OrderItem.objects.bulk_create(order_items_to_create)
            
            ProductVariant.objects.bulk_update(variants_to_update,['stock'])
                
            cart_items.delete()
            
            request.session['order_id'] = order.order_id
            
        try:
            user_email = order.user.email
            
            plain_message = f'Order Successful Places!.'
            html_message = render_to_string('email/order_success_mail.html',{'order':order,'items': order.items.all(),})
            msg = EmailMultiAlternatives(
                body = plain_message,
                subject='Order Successful',
                to=[user_email],
            )
            msg.attach_alternative(html_message,'text/html')
            msg.send()
        except Exception as e:
            print(f"Email sending failed: {e}")
            
        return render(request, 'orders/order_success.html', {'order': order})
            
    except ValueError as e:
        messages.error(request, f"Value Error: {str(e)}")
        return redirect('cart')
        
    except Exception as e:
        # Log this error in production!
        print(f"Order Placement Error: {e}")
        messages.error(request, "An error occurred while placing your order. Please try again.")
        return redirect('checkout')

@never_cache
@login_required
def order_details_view(request,order_id):
    user = request.user
        
    order = get_object_or_404(OrderMain,order_id = order_id ,user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order' : order,
        'order_items' : order_items,
    }
    return render(request,'orders/order_details.html',context)

@never_cache
@login_required
def download_invoice_view(request, order_id):
    order = get_object_or_404(OrderMain, order_id=order_id)

    context = {
        'order': order,
        'items': order.items.all(),
        'company_name': "SecondStrap", 
        'company_email': "support@secondstrap.com",
    }
    
    pdf = render_to_pdf('invoice/invoice.html', context)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{order.order_id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
        
    return HttpResponse("Not found")

@login_required
@require_POST
@never_cache
def return_order_view(request, order_id):
    try: 
        data = json.loads(request.body)
        list_return_items = data.get('returns', [])
        
        if not list_return_items:
            return JsonResponse({'status': 'error', 'message': 'No items selected for return.'}, status=400)
        
        order = get_object_or_404(OrderMain, order_id=order_id, user=request.user)
        
        if order.order_status !=  'delivered':
            return JsonResponse({"status" : "error" , "message" : "Order has not been delivered yet."},status=400)
        
        current_date = timezone.now()
        delivered_date = order.updated_at
        
        difference = current_date - delivered_date
        if difference.days > 7:
            return JsonResponse({"status" : "error","message" : "Return period expired. You can only return items within 7 days of delivery."},status=400)
        
        with transaction.atomic():
            items_updated_count = 0
            for item in list_return_items:
                item_id = item.get('item_id')
                reason = item.get('reason')
                note = item.get('note')
                
                
                order_item = get_object_or_404(OrderItem, id=item_id, order=order)
                if order_item.status in ['returned', 'return_requested', 'cancelled', 'partially_cancelled']:
                    continue
                
                order_item.status = 'return_requested'
                order_item.save()

                ReturnOrder.objects.create(
                    order=order,
                    user=request.user,
                    item=order_item,
                    return_reason=reason,
                    return_note=note,
                    return_status='return_requested'
                )
                items_updated_count += 1
                
            if items_updated_count == 0:
                return JsonResponse({'status': 'error', 'message': 'Selected items are not eligible for return.'}, status=400)

            total_items = order.items.count()
            
            print(f"total items : {total_items}")
            
            non_active_items = order.items.filter(
                status__in=['return_requested', 'returned', 'cancelled', 'partially_cancelled']
            ).count()
            
            if total_items == non_active_items:
                order.order_status = 'return_requested'
                order.save()
        
        return JsonResponse({'status': 'success', 'message': 'Return request submitted successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    
    except Exception as e:
        print(f"Error: {e}")  
        return JsonResponse({'status': 'error', 'message': 'Something went wrong'}, status=500)

@login_required
@never_cache
def cancel_return_order_view(request, order_id):
    order = get_object_or_404(OrderMain, order_id=order_id, user=request.user)
    return_items = ReturnOrder.objects.filter(order=order, return_status='return_requested')
    if not return_items.exists():
        messages.warning(request, 'No active return requests found for this order')
        return redirect('order_details', order_id=order_id)
        
    try:
        with transaction.atomic():
            for return_entry in return_items:
                print(f"return Items : {return_entry}")
                order_item = return_entry.item
                order_item.status = 'delivered'
                order_item.save()
    
            return_items.update(return_status = 'return_canceled')
                
            has_other_returns = order.items.filter(status = 'return_requested').exists()
            if not has_other_returns:
                order.order_status = 'delivered'
                order.is_returned = False
                order.save()
                
        messages.success(request, "Return request cancelled Successfully.")
        
    except Exception as e:
        print(f"Error cancelling return: {e}") 
        messages.error(request, 'An error occurred')

    return redirect('order_details', order_id=order_id)
@login_required
@never_cache
@require_POST
@transaction.atomic
def cancel_order_view(request, order_id):
    order = get_object_or_404(OrderMain,order_id=order_id,user=request.user)

    if order.order_status in ['shipped', 'out_for_delivery', 'delivered', 'cancelled']:
        return JsonResponse({'status': 'error', 'message': 'Cannot cancel: Order is already processed.'},status=400)

    try:
        data = json.loads(request.body)
        cancels = data.get('cancels', [])

        if not cancels:
            return JsonResponse({'status': 'error', 'message': 'No items selected for cancellation.'},status=400)

        cancel_order = CancelOrder.objects.create(order=order,user=request.user)

        total_refund = Decimal('0.00')

        total_items = order.get_total_item_count or 1
        coupon_per_item = (order.coupon_discount / total_items if order.coupon_discount else Decimal('0.00'))

        for entry in cancels:
            item_id = entry.get('item_id')
            reason = entry.get('reason')
            note = entry.get('note', '').strip()

            if not item_id or not reason or not note:
                return JsonResponse(
                    {'status': 'error', 'message': 'Reason and note are required for all items.'},
                    status=400
                )

            item = get_object_or_404(OrderItem, id=item_id, order=order)

            if item.status in ['cancelled', 'returned']:
                continue

            item_refund = Decimal('0.00')

            if order.payment_method in ['razorpay', 'wallet']:
                item_total = item.price_at_purchase * item.quantity
                item_coupon_share = coupon_per_item * item.quantity
                item_refund = item_total - item_coupon_share

                total_refund += item_refund

            CancelItem.objects.create(
                cancel_order=cancel_order,
                order_item=item,
                quantity=item.quantity,
                reason=reason,
                note=note,
                refund_amount=item_refund
            )

            # Update item status
            item.status = 'cancelled'
            item.save(update_fields=['status'])

            # Restore stock
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=['stock'])

        # Update cancel order
        cancel_order.refund_amount = total_refund
        cancel_order.is_full_cancel = not order.items.exclude(status='cancelled').exists()
        cancel_order.cancel_status = 'completed'
        cancel_order.save(update_fields=[
            'refund_amount', 'is_full_cancel', 'cancel_status'
        ])

        # Update main order
        order.order_status = (
            'cancelled' if cancel_order.is_full_cancel else 'partially_cancelled'
        )
        order.save(update_fields=['order_status'])

        # Wallet refund
        if total_refund > 0:
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            Wallet.objects.filter(pk=wallet.pk).update(
                balance=F('balance') + total_refund
            )

            Transaction.objects.create(
                wallet=wallet,
                transaction_type=TransactionType.CREDIT,
                amount=total_refund,
                description=f"Refund for Order {order.order_id}",
                status=TransactionStatus.COMPLETED,
                related_order=order
            )

        return JsonResponse(
            {
                'status': 'success',
                'message': 'Cancellation completed successfully. Refund credited to wallet.'
            },
            status=200
        )

    except Exception as e:
        print("Cancel Error:", e)
        transaction.set_rollback(True)
        return JsonResponse(
            {'status': 'error', 'message': 'Something went wrong while cancelling the order.'},
            status=500
        )
