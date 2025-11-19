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

        data = json.loads(request.body)
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone_input = data.get('phone')

        if not first_name or not last_name :
            return JsonResponse({'status': 'error', 'message': 'Name fields cannot be empty'})
        
        user.first_name = first_name
        user.last_name = last_name
        
        if phone_input :
            if len(phone_input) > 10 or len(phone_input) < 10:
                return JsonResponse({'status' : 'error' , 'message' : 'Please Enter a Valid Number !!'})
            user.phone = phone_input

        user.save()

        return JsonResponse({
            'status' : 'success',
            'message' : 'Profile updated successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as ex:
        return JsonResponse({'status': 'error', 'message': str(ex)})



class ProfileAddressView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_addresses.html"
    
class ProfilePaymentView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_payment.html"

class ProfileOrderView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_orders.html"

class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "userprofile/wallet.html"