from django.utils.crypto import get_random_string
import string
from accounts.models import *
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

def generate_alphabetical_code(length=4):
    '''
        This is used to gnerate A-Z OTP
    '''
    allowed_chars = string.ascii_uppercase

    code = get_random_string(length=length, allowed_chars=allowed_chars)

    return code

def send_email_otp(user, request):
    # delete old OTPs
    EmailOTP.objects.filter(user=user).delete()

    otp = generate_alphabetical_code()
    EmailOTP.objects.create(user=user, otp=otp)

    html_message = render_to_string(
        'email/email_verification.html',
        {'otp_code': otp, 'first_name': user.first_name}
    )

    msg = EmailMultiAlternatives(
        subject='Email Verification OTP',
        body=f'Your OTP code is {otp}',
        to=[user.email],
    )
    msg.attach_alternative(html_message, "text/html")
    msg.send()

    request.session['email_to_verify'] = user.email
