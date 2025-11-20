import json
from django.shortcuts import redirect
from django.views.generic import TemplateView,DetailView,View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import EmailOTP,CustomUser
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .utils import generate_alphabetical_code
# Create your views here.

class SecureUserMixin(LoginRequiredMixin):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
class ProfileView(SecureUserMixin, TemplateView):
    template_name = 'userprofile/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

@login_required
@require_POST
def edit_action(request):
    try :
        user = request.user
        is_change = False

        data = json.loads(request.body)
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone = data.get('phone')

        if not first_name or not last_name :
            return JsonResponse({
                'status': 'error', 
                'message': 'Name fields cannot be empty'
            })  
         
        if  first_name != user.first_name:
            user.first_name = first_name
            is_change = True

        if last_name != user.last_name:
            user.last_name = last_name
            is_change = True

        if email and  email != user.email:
            user.email = email
            user.is_verified = False
            is_change = True

        
        if phone is not None:
            phone_str = str(phone).strip()

            if not phone_str.isdigit() or len(phone) != 10:
                return JsonResponse({
                    'status' : 'error',
                    'message' : 'Please enter the correct Phone number'
                })

            if phone_str != getattr(user,'phone',''):
                user.phone = phone_str
                is_change = True


        if is_change:
            user.save()
            return JsonResponse({
                'status' : 'success',
                'message' : 'Profile  updated successfully'
            })
        
        return JsonResponse({
                'status' : 'success',
                'message' : 'No changes detected'
            })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as ex:
        return JsonResponse({'status': 'error', 'message': str(ex)})

@login_required
def verify_action(request):
    try:
        user = request.user
        OTP = generate_alphabetical_code()
        # print(OTP)
        EmailOTP.objects.create(user=request.user,otp=OTP)
        plain_message = f'Your OTP code is {OTP}'
        html_message = render_to_string('email/email_verification.html', {'otp_code': OTP,'first_name':user.first_name})
        msg = EmailMultiAlternatives(
            body=plain_message,
            subject='Email Verification OTP',
            to=[user.email],
        )
        msg.attach_alternative(html_message,"text/html")
        msg.send()
        request.session['otp_code'] = OTP
        request.session['email_to_verify'] = user.email
        return JsonResponse({
            'status' : 'success' ,
            'message' : 'OTP sent successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status' : 'error',
            'message' : str(e) 
        })

@login_required
@require_POST
def otp_verification(request):
    user_id = request.session.get('email_to_verify')
    if not user_id:
        return JsonResponse({
            'status' :'error',
            'message' : 'No Pending verfication Found'
        })
    
    try :
        user = CustomUser.objects.get(email=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'status' : 'error',
            'message' : 'User Not Found'
        })

    otp = request.POST.get('otp')

    if not otp :
        return JsonResponse({
            'status' :'error',
            'message' : 'User Not Found'
        })
    try:
        otp_record = EmailOTP.objects.filter(user=user,otp=otp).latest('-created_at')
    except EmailOTP.DoesNotExist:
        return JsonResponse({
            'status' : 'error',
            'message': 'OTP is not Valid . Try Again'
        })

    if otp_record.is_valid():
        user.is_verified = True
        user.save()
        request.session.pop('email_to_verify',None)
        otp_record.delete()
        return JsonResponse({
            'status' : 'success',
            'message': 'Email Verified Successfully'
        })
    else:
        return JsonResponse({
            'status' : 'error',
            'message' : 'OTP is not Valid . Try again'
        })



class ProfileAddressView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_addresses.html"
    
class ProfilePaymentView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_payment.html"

class ProfileOrderView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_orders.html"

class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "userprofile/wallet.html"