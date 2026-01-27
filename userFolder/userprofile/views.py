import json
import logging
import cloudinary
import cloudinary.uploader
logger = logging.getLogger(__name__)
from django.shortcuts import render,redirect
from django.contrib import messages
from django.views.generic import TemplateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST,require_http_methods
from django.http import JsonResponse
from accounts.models import EmailOTP,CustomUser
from .utils import send_email_otp
from .forms import AddressForm,ChangePasswordForm
from .models import Address
from django.db import IntegrityError
from django.contrib.auth import update_session_auth_hash
from userFolder.order.models import OrderMain
from userFolder.referral.models import *

from .decorators import ajax_login_required 
from django.urls import reverse


# Create your views here.

class SecureUserMixin(LoginRequiredMixin):
    login_url = 'login'   # optional but recommended

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_active :
            messages.error(request, "Your account is blocked by admin.")
            return redirect('login')

        if not user.is_verified:
            messages.warning(request, "Please verify your email to continue.")
            messages.info(request, "OTP send to your Mail.")
            send_email_otp(user, request)
            return redirect('otp_page')  

        return super().dispatch(request, *args, **kwargs)
class ProfileView(SecureUserMixin, TemplateView):
    template_name = 'userprofile/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user_referral,_ = Referral.objects.get_or_create(user=self.request.user)
        total_refer_count = ReferralUsage.objects.filter(referrer=user_referral,is_reward_credited=True).count()
        print(total_refer_count)
        context['user'] = self.request.user
        context['referral_code'] = user_referral.referral_code
        context['total_refer_count'] = total_refer_count
        return context

@ajax_login_required
@require_POST
def edit_action(request):
    try:
        user = request.user
        data = json.loads(request.body)

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone')

        is_change = False
        is_email_change = False

        if not first_name or not last_name:
            return JsonResponse({'status': 'error', 'message': 'Name fields cannot be empty'})

        if first_name != user.first_name:
            user.first_name = first_name
            is_change = True

        if last_name != user.last_name:
            user.last_name = last_name
            is_change = True

        if email and email != user.email:
            if CustomUser.objects.exclude(pk=user.pk).filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'})

            user.email = email
            user.is_verified = False
            is_change = True
            is_email_change = True

        if phone is not None:
            phone = str(phone).strip()
            if not phone.isdigit() or len(phone) != 10:
                return JsonResponse({'status': 'error', 'message': 'Invalid phone number'})

            if phone != getattr(user, 'phone', ''):
                user.phone = phone
                is_change = True

        if not is_change:
            return JsonResponse({'status': 'success', 'message': 'No changes detected'})

        user.save()

        if is_email_change:
            request.session['is_email_change'] = True
            send_email_otp(user, request)
            return JsonResponse({
                'status': 'email_changed',
                'message': 'Email changed. OTP verification required.',
                'redirect_url': reverse('otp_page')
            })

        return JsonResponse({'status': 'success', 'message': 'Profile updated successfully'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@ajax_login_required
@require_POST
def resend_otp_view(request):
    if 'is_email_change' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    try:
        send_email_otp(request.user, request)
        return JsonResponse({'status': 'success', 'message': 'OTP resent successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@ajax_login_required
def otp_page(request):
    if 'is_email_change' not in request.session:
        return redirect('profile')

    return render(request, 'userprofile/verify_otp.html')

        
@ajax_login_required
@require_POST
def verify_otp_axios(request):
    if 'is_email_change' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Invalid session'})

    user_email = request.session.get('email_to_verify')
    if not user_email:
        return JsonResponse({'status': 'error', 'message': 'No pending verification'})

    otp = request.POST.get('otp', '').strip()
    if not otp:
        return JsonResponse({'status': 'error', 'message': 'OTP is required'})

    try:
        user = CustomUser.objects.get(email=user_email)
        otp_record = EmailOTP.objects.filter(user=user, otp=otp).latest('created_at')
    except (CustomUser.DoesNotExist, EmailOTP.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Invalid OTP'})

    if not otp_record.is_valid():
        return JsonResponse({'status': 'error', 'message': 'OTP expired or invalid'})

    user.is_verified = True
    user.save()

    EmailOTP.objects.filter(user=user).delete()
    request.session.pop('email_to_verify', None)
    request.session.pop('is_email_change', None)

    return JsonResponse({'status': 'success', 'message': 'Email verified successfully'})

class ProfileAddressView(SecureUserMixin, ListView):
    model=Address
    template_name = "userprofile/profile_addresses.html"
    context_object_name ='addresses'

    def get_queryset(self):
        queryset =  super().get_queryset()
        return Address.objects.filter(user=self.request.user)

@require_http_methods(["GET","POST"])
@ajax_login_required
@never_cache
def manage_address(request,address_id=None):
    if request.method == "GET" and address_id is not None:
        try:
            address = Address.objects.get(id=address_id,user = request.user)
            address_data = {
                'id': address.id,
                'full_name': address.full_name,
                'address_line_1': address.address_line_1,
                'address_line_2': address.address_line_2,
                'city': address.city,
                'state': address.state,
                'postal_code': address.postal_code,
                'phone_number': address.phone_number,
                'country': address.country,
                'is_default': address.is_default,
                'address_type': address.address_type,
            }
            return JsonResponse({'status':'success','address':address_data})
        except Address.DoesNotExist:
            return JsonResponse({'status' : 'error','message' : 'Address Not Found'},status=404)
        except Exception as e :
            return JsonResponse({'status':'error','message': str(e) },status=500)
        
    if request.method == "POST" :
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "error", 
                "message": "Invalid JSON body"
            },
            status = 400,
            )
        
        address_id = data.get("address_id")
        
        if address_id:
            try:
                address = Address.objects.get(id=address_id,user=request.user)
            except Address.DoesNotExist :
                return JsonResponse({
                    'status' : 'error',
                    'message' : 'Address Not Found'
                },
                status = 404
                )
            except (TypeError, ValueError):
                return JsonResponse({
                    'status' : 'error',
                    'message' : 'Invalid address ID'
                },
                status = 400
                )
        else:
            address = Address(user=request.user)

        form = AddressForm(data,instance=address)

        if form.is_valid():
            if form.cleaned_data.get('is_default'):
                request.user.address_set.filter(is_default=True).update(is_default=False)
            address = form.save(commit=False)
            if not request.user.address_set.exists():
                address.is_default = True
            address.save()
            return JsonResponse({
                'status' : 'success',
                'message' : 'Address Saved'
            },
            status = 200
            )
        
        return JsonResponse({
            "status": "error",
            "errors": form.errors,  
        },
        status=400
        )

@never_cache
@ajax_login_required
@require_POST
def delete_address(request, address_id=None):
    if not address_id:
        return JsonResponse({'status': 'error', 'message': 'Address ID is required'})

    try:
        address = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Address not found!'})

    other_address = request.user.address_set.exclude(id=address_id)
    if not other_address.exists():
        return JsonResponse({'status': 'error', 'message': 'You must have at least one address'})

    was_default = address.is_default
    address.delete()
    
    if was_default:
        new_default = other_address.order_by('id').first()
        if new_default:
            new_default.is_default = True
            new_default.save(update_fields=['is_default'])

    return JsonResponse({'status': 'success', 'message': 'Address Deleted Successfully'})

class ProfileOrderView(SecureUserMixin, ListView):
    model = OrderMain
    context_object_name = 'orders'
    template_name = "userprofile/profile_orders.html"
    paginate_by = 10  

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = OrderMain.objects.filter(user=self.request.user).exclude(order_status='draft').order_by('-created_at')
            return queryset
        return OrderMain.objects.none()

@never_cache
@ajax_login_required
def change_password(request):
    if request.method == 'POST' :
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            pass1 = form.cleaned_data['new_password']
    
            user = request.user
            try :
                user.set_password(pass1)
                user.save()
                # keep the user logged in after changing password
                update_session_auth_hash(request, user)
                return JsonResponse({
                    'status' : 'success',
                    'message' : 'Password Changed Successfuly. backend'
                })
            except (IntegrityError, ValueError) as e:
                logger.error(f"Password change failed for user {user.id}: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'Something went wrong while updating the password.'})
        else:
            errors = form.errors.as_json()
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data submitted.',
                'errors': errors,
            })
    form = ChangePasswordForm()
    return render(request,'userprofile/change_password.html',{'form':form})

@ajax_login_required
@require_POST
def update_profile_picture(request):
    file = request.FILES.get('profile_image')
    if file:
        try :
            upload_image =cloudinary.uploader.upload(
                file,
                folder = 'profile_avatars',
                public_id = f'avator_{request.user.id}',
                overwrite=True,
                resource_type="image"
            )
            image_url = upload_image.get('secure_url')

            user = request.user
            user.profile = image_url
            user.save()
            return JsonResponse({'status':'success','message':'Profile updated succefully','image_url':image_url})
        except Exception as e :
            return JsonResponse({'status':'error','message':str(e)})
    return JsonResponse({'status' : 'error','message':'No file found.'})
