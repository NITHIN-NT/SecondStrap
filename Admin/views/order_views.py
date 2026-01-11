import logging
logger = logging.getLogger(__name__)
import json
from django.shortcuts import render,get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.db.models import Count,Sum,F
from django.db import transaction
from django.http import JsonResponse

from products.models import Product,Category
from userFolder.order.models import OrderItem,OrderMain,ORDER_STATUS_CHOICES,ADMIN_ORDER_STATUS_CHOICES,PAYMENT_STATUS_CHOICES,ReturnOrder
from userFolder.wallet.models import Wallet,Transaction,TransactionStatus,TransactionType

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class StockManagementView(ListView):
    model = Product
    context_object_name = "products"
    template_name = "stock/stock_management.html"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            Product.objects
            .prefetch_related("variants", "variants__size")
            .annotate(
                total_stock=Sum("variants__stock"),
                variant_count=Count("variants")
            )
        )

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context['custom_page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=2,
                on_ends=1
            )

        query_params = self.request.GET.copy()
        query_params.pop("page", None)

        context.update({
            "query_params": query_params.urlencode(),
            "categorys": Category.objects.all(),
            "search": self.request.GET.get("search", ""),
            "selected_category": self.request.GET.get("category", ""),
        })

        return context

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class AdminOrderView(ListView):
    model = OrderMain
    context_object_name = 'orders'
    template_name ='order/order.html'
    ordering = ['-created_at']
    paginate_by = 9
    
    def get_queryset(self):
        queryset =  super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        payment = self.request.GET.get('payment')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if search:
            queryset = queryset.filter(order_id__icontains = search.strip())
            
        if status:
            queryset = queryset.filter(order_status__icontains = status)
        
        if payment:
            queryset = queryset.filter(payment_status__icontains = payment)
            
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__range =[start_date,end_date])
        elif start_date :
            queryset = queryset.filter(created_at__date__gte=start_date)
        elif end_date :
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset
        
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context['custom_page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=5,
                on_ends=1
            )

        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        encoded = query_params.urlencode()
        context['query_params'] = encoded  

        context['order_status_choices'] = ORDER_STATUS_CHOICES
        context['payment_status_choices'] = PAYMENT_STATUS_CHOICES
        return context
   
@login_required
@never_cache
@staff_member_required(login_url='admin_login')
def admin_order_detailed_view(request,order_id):
    order = get_object_or_404(OrderMain, order_id=order_id)
    context = {
        'order' : order,
        'order_status_choices': ADMIN_ORDER_STATUS_CHOICES, 
        'payment_status_choices': PAYMENT_STATUS_CHOICES,
    }
    return render(request,'order/order_detailed.html',context)
  
@staff_member_required(login_url='admin_login')
@transaction.atomic
@never_cache
def admin_order_status_update(request,order_id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)
    
    try :
        order_status = request.POST.get('order_status')
        payment_status = request.POST.get('payment_status')
        
        if not order_status or not payment_status:
            return JsonResponse(
                {"status": "error", "message": "Missing status values"},
                status=400
            )
        
        order = get_object_or_404(OrderMain,order_id=order_id)
        
        if order.order_status != 'cancelled' and order_status == 'cancelled':
            for item in order.items.all():
                if item.variant:
                    item.variant.stock = F('stock') + item.quantity
                    item.variant.save()
        
        order.order_status = order_status
        order.payment_status = payment_status
        order.save()
        
        ignored_statuses = [
            'cancelled', 
            'returned', 
            'return_requested', 
            'return_approved', 
            'return_rejected', 
            'return_canceled'
        ]
        order.items.exclude(status__in = ignored_statuses).update(status=order_status)
            
        return JsonResponse({"status" : 'success' , "message":"Order Status updated !"})
    except Exception as e :
        print(f"Error updating order {order_id}: {str(e)}")
        logger.exception("Failed to update order status for order %s", order_id)
        return JsonResponse({'status': 'error', 'message': 'Update failed'})
    
@staff_member_required(login_url='admin_login')
@transaction.atomic
@never_cache
def manage_return_request(request, item_id, order_id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid Request"}, status=405)

    try:
        data = json.loads(request.body)
        action = data.get('action')

        if action not in {'approve', 'reject', 'returned'}:
            return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)

        order = get_object_or_404(OrderMain, order_id=order_id)
        order_item = get_object_or_404(OrderItem, id=item_id, order=order)
        product_variant = order_item.variant

        return_item = ReturnOrder.objects.filter(order=order, item=order_item).first()
        if not return_item:
            return JsonResponse({"status": "error", "message": "No return request found"}, status=400)

        if action == 'approve':
            if order_item.status != 'return_requested':
                return JsonResponse({"status": "error", "message": "Item is not in requested state"}, status=400)

            order_item.status = 'return_approved'
            return_item.return_status = 'return_approved'
            
            if order.get_total_item_count > 1:
                order.order_status = 'return_approved'
                order.save()

            order_item.save()
            return_item.save()

            return JsonResponse({"status": "success", "message": "Return approved"})

        elif action == 'reject':
            if order_item.status != 'return_requested':
                return JsonResponse({"status": "error", "message": "Item is not in requested state"}, status=400)

            order_item.status = 'delivered'
            order_item.is_returned = False
            return_item.return_status = 'return_rejected'

            if not order.items.filter(status='return_requested').exists():
                order.order_status = 'delivered'

            order_item.save()
            return_item.save()
            order.save()

            return JsonResponse({"status": "success", "message": "Return rejected"})

        elif action == 'returned':
            if order_item.status != 'return_approved':
                return JsonResponse(
                    {"status": "error", "message": "Item must be approved before receiving"},
                    status=400
                )

            order_item.status = 'returned'
            order_item.is_returned = True
            return_item.return_status = 'returned'

            item_total = order_item.price_at_purchase * order_item.quantity
            refund_amount = item_total

            if order.coupon_discount:
                total_items = order.get_total_item_count
                each_item_share = order.coupon_discount / total_items
                refund_amount = item_total - (each_item_share * order_item.quantity)

            return_item.refund_amount = refund_amount

            if product_variant:
                product_variant.__class__.objects.filter(
                    pk=product_variant.pk
                ).update(stock=F('stock') + order_item.quantity)

            active_items_exist = order.items.filter(is_returned=False).exists()
            order.order_status = 'partially_returned' if active_items_exist else 'returned'

            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            Wallet.objects.filter(pk=wallet.pk).update(
                balance=F('balance') + refund_amount
            )

            Transaction.objects.create(
                wallet=wallet,
                transaction_type=TransactionType.CREDIT,
                amount=refund_amount,
                description=f"Refund for Item: {order_item.variant.product.name if order_item.variant else order_item.product.name}",
                status=TransactionStatus.COMPLETED,
                related_order=order
            )

            order_item.save()
            return_item.save()
            order.save()

            return JsonResponse({"status": "success", "message": "Item marked as received and refunded"})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    except Exception as e:
        print("Return exception:", str(e))
        return JsonResponse({"status": "error", "message": "Internal Server Error"}, status=500)
