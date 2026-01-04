from django.core.mail import EmailMultiAlternatives 
from django.template.loader import render_to_string
from django.conf import settings

def send_html_mail(subject,template_name,context,to_email,plain_text=None):
    html_message = render_to_string(template_name,context) 

    if not plain_text:
        plain_text = "Please view this message in an HTML compatible email client."


    msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email = settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
    msg.attach_alternative(html_message,"text/html")
    msg.send()
    
def apply_sale_report_filters(request, orders):
    product_id = request.GET.get('product')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    item_count = request.GET.get('item_count')
    status = request.GET.get('status')
    filter_type = request.GET.get('filter_type')

    if filter_type == 'monthly':
        month = request.GET.get('month')
        year = request.GET.get('year')
        if month and year:
            orders = orders.filter(
                created_at__month=month,
                created_at__year=year
            )
    elif filter_type == 'yearly':
        year = request.GET.get('year')
        if year:
            orders = orders.filter(created_at__year=year)

    if product_id:
        orders = orders.filter(items__variant__product_id=product_id)

    if start_date:
        orders = orders.filter(updated_at__date__gte=start_date)

    if end_date:
        orders = orders.filter(updated_at__date__lte=end_date)

    if item_count:
        orders = orders.filter(items_count=item_count)

    if status:
        orders = orders.filter(order_status=status)

    return orders.distinct()