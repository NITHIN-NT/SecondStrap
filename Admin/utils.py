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