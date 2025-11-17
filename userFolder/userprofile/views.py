from django.shortcuts import redirect
from django.views.generic import TemplateView,DetailView,View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
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
    
class ProfileAddressView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_addresses.html"
    
class ProfilePaymentView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_payment.html"

class ProfileOrderView(SecureUserMixin, TemplateView):
    template_name = "userprofile/profile_orders.html"

class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "userprofile/wallet.html"