import json
import logging
import cloudinary
import cloudinary.uploader
logger = logging.getLogger(__name__)
from django.shortcuts import redirect,render
from django.views.generic import TemplateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST,require_http_methods
from django.http import JsonResponse
from accounts.models import EmailOTP,CustomUser
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .utils import generate_alphabetical_code
from .forms import AddressForm,ChangePasswordForm
from django.contrib import messages
from .models import Address
from django.db import IntegrityError
from django.contrib.auth import update_session_auth_hash
from userFolder.order.models import OrderMain

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

            if not phone_str.isdigit() or len(phone_str) != 10:
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
    user_email = request.session.get('email_to_verify')
    if not user_email:
        return JsonResponse({
            'status' :'error',
            'message' : 'No Pending verification Found'
        })
    
    try :
        user = CustomUser.objects.get(email=user_email)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'status' : 'error',
            'message' : 'OTP Not found'
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

class ProfileAddressView(SecureUserMixin, ListView):
    model=Address
    template_name = "userprofile/profile_addresses.html"
    context_object_name ='addresses'

    def get_queryset(self):
        queryset =  super().get_queryset()
        return Address.objects.filter(user=self.request.user)

@require_http_methods(["GET","POST"])
@login_required
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
@login_required
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
class ProfilePaymentView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_payment.html"

class ProfileOrderView(SecureUserMixin, ListView):
    model = OrderMain
    context_object_name = 'orders'
    template_name = "userprofile/profile_orders.html"
    paginate_by = 10  

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = OrderMain.objects.filter(user=self.request.user).order_by('-created_at')
            return queryset
        return OrderMain.objects.none()

@never_cache
@login_required
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

@login_required
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