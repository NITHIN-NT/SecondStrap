from django.shortcuts import redirect
from django.views.generic import TemplateView,DetailView,View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
# Create your views here.
class LoggedInRedirectMixin:
    """
    A mixin to redirect authenticated users away from a page.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('Home_page_user') 
        return super().dispatch(request, *args, **kwargs)

method_decorator(never_cache,name='dispatch')
class ProfileView(LoginRequiredMixin,TemplateView):
    template_name = 'userprofile/profile.html'
    model = get_user_model()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['user'] = self.request.user
        return context
    
class ProfileAddressView(LoginRequiredMixin,TemplateView):
    template_name= "userprofile/profile_addresses.html"
    
class ProfilePaymentView(LoginRequiredMixin,TemplateView):
    template_name= "userprofile/profile_payment.html"

class ProfileOrderView(LoginRequiredMixin,TemplateView):
    template_name= "userprofile/profile_orders.html"

class ProfileWalletView(LoginRequiredMixin,TemplateView):
    template_name= "userprofile/wallet.html"

