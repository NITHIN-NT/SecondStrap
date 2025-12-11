from django.shortcuts import render
from django.views.generic import TemplateView
from .models import Wallet
from userFolder.userprofile.views import SecureUserMixin

# Create your views here.
class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "wallet/wallet.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        user_wallet = Wallet.objects.select_related('user').prefetch_related('transactions').get(user=self.request.user)
        context['wallet'] = user_wallet
        return context
