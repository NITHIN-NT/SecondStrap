from django.shortcuts import render
from django.db.models import Sum, Count, Avg
from userFolder.order.models import OrderItem, OrderMain, ORDER_STATUS_CHOICES
from products.models import Product, Category
from openpyxl import Workbook
from django.db.models import Count
from xhtml2pdf import pisa
from django.http import JsonResponse,HttpResponse
from django.template.loader import render_to_string,get_template
from ..utils import apply_sale_report_filters
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache

@staff_member_required(login_url='admin_login')
@never_cache
def sale_report_view(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    base_orders = (
        OrderMain.objects
        .select_related()
        .prefetch_related('items')
        .annotate(items_count=Count('items'))
        .order_by('-created_at')
    )
    
    orders = apply_sale_report_filters(request, base_orders)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders, 15)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        if int(page_number) < 1:
            page_obj = paginator.page(1)
        else:
            page_obj = paginator.page(paginator.num_pages)

    
    total_sale = OrderMain.objects.aggregate(total=Sum('final_price'))['total'] or 0
    total_unit_sold = OrderItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
    avg_sale = OrderMain.objects.aggregate(avg_total=Avg('final_price'))['avg_total'] or 0

    filter_sale_total = orders.aggregate(total=Sum('final_price'))['total'] or 0
    filter_unit_sold = OrderItem.objects.filter(order__in=orders).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    filter_avg_sale = orders.aggregate(avg_total=Avg('final_price'))['avg_total'] or 0

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        orders_html = render_to_string(
            'sale_report/_orders_rows.html',
            {'orders': page_obj, 'page_obj': page_obj},
            request=request
        )

        return JsonResponse({
            'filter_sale_total': float(filter_sale_total),
            'filter_unit_sold': int(filter_unit_sold),
            'filter_avg_sale': float(filter_avg_sale),
            'orders_html': orders_html,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'number': page_obj.number,
            'num_pages': paginator.num_pages
        })

    context = {
        'products': products,
        'categories': categories,

        'total_sale': total_sale,
        'total_unit_sold': total_unit_sold,
        'avg_sale': avg_sale,

        'orders': page_obj,
        'page_obj': page_obj,
        'order_status': ORDER_STATUS_CHOICES,

        'filter_sale_total': filter_sale_total,
        'filter_unit_sold': filter_unit_sold,
        'filter_avg_sale': filter_avg_sale,
    }

    return render(request, 'sale_report/sales_report.html', context)    

@staff_member_required(login_url='admin_login')
@never_cache
def sales_report_pdf(request):
    orders = (
        OrderMain.objects
        .prefetch_related('items')
        .annotate(items_count=Count('items'))
        .order_by('-created_at')
    )

    orders = apply_sale_report_filters(request, orders)

    summary = {
        'total_revenue': orders.aggregate(total=Sum('final_price'))['total'] or 0,
        'total_units': OrderItem.objects.filter(order__in=orders).aggregate(
            total=Sum('quantity')
        )['total'] or 0,
        'total_orders': orders.count()
    }

    template = get_template('sale_report/pdf/sales_report_pdf.html')
    html = template.render({
        'orders': orders,
        'summary': summary
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response

@staff_member_required(login_url='admin_login')
@never_cache
def sales_report_excel(request):
    orders = (
        OrderMain.objects
        .prefetch_related('items')
        .annotate(items_count=Count('items'))
        .order_by('-created_at')
    )

    orders = apply_sale_report_filters(request, orders)

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    ws.append(["Date", "Order ID", "Units", "Revenue", "Status"])

    for o in orders:
        ws.append([
            o.created_at.strftime('%d-%m-%Y'),
            o.order_id,
            o.items_count,
            float(o.final_price),
            o.get_order_status_display()
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
    wb.save(response)
    return response