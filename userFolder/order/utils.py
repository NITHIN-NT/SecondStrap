from django.template.loader import get_template, render_to_string
from django.core.mail import EmailMultiAlternatives
from io import BytesIO
from django.http import HttpResponse
from xhtml2pdf import pisa

def send_order_success_email(order):
    """
    Utility to send order success email.
    """
    try:
        user_email = order.user.email
        html_message = render_to_string(
            'email/order_success_mail.html',
            {'order': order, 'items': order.items.all()}
        )
        msg = EmailMultiAlternatives(
            subject='Order Successful - SecondStrap',
            body='Your order has been placed successfully!',
            to=[user_email],
        )
        msg.attach_alternative(html_message, 'text/html')
        msg.send()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None