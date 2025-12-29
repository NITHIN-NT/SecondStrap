import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import F,Sum
from django.db import transaction
from django.views.generic import TemplateView

from .models import *
from userFolder.wallet.models import *
from userFolder.userprofile.views import SecureUserMixin

def referral_view(request):
    if not request.user.is_authenticated:
        return redirect('signup')
    
    if request.method == "POST":
        data = json.loads(request.body)
        referral_code = data.get('referral_code')
        user = request.user
        
        # valid code
        try:
            referral = Referral.objects.get(referral_code=referral_code)
        except Referral.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid referral code'})
        
        # user using his own code checking
        if referral.user == user:
            return JsonResponse({'status': 'error', 'message': 'Cannot use your own referral code'})
        
        # any referral before
        if ReferralUsage.objects.filter(receiver=user, referrer=referral).exists():
            return JsonResponse({'status': 'error', 'message': 'You have already used this referral code'})
        
        
        try:
            with transaction.atomic():

                referral_usage = ReferralUsage.objects.create(
                    referrer=referral,
                    receiver=user,
                    referral_reward=Decimal('49'),
                    status=ReferralUsage.Status.ACTIVE,
                    is_reward_credited=False
                )
                
                # Wallet transaction for Referrer
                referrer_wallet, _ = Wallet.objects.get_or_create(user=referral.user)
                referrer_wallet.balance += Decimal('49')
                referrer_wallet.save()
                
                Transaction.objects.create(
                    wallet=referrer_wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=Decimal('49'),
                    description=f"{user.first_name} signed up using your referral code",
                    status=TransactionStatus.COMPLETED
                )
                
                # Wallet transaction for Receiver
                receiver_wallet, _ = Wallet.objects.get_or_create(user=user)
                receiver_wallet.balance += Decimal('49')
                receiver_wallet.save()
                
                Transaction.objects.create(
                    wallet=receiver_wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=Decimal('49'),
                    description=f"Referral bonus from {referral.user.first_name}",
                    status=TransactionStatus.COMPLETED
                )
                
                referral_usage.is_reward_credited = True
                referral_usage.status=ReferralUsage.Status.REWARDED
                referral_usage.save()
                
                referral.used_count = F('used_count') + 1
                referral.save()
                
            return JsonResponse({"status": 'success', 'message': 'Referral applied successfully'})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Something went wrong: {str(e)}"})
    
    return render(request, 'referral/referral.html')

class ReferralDetailView(SecureUserMixin,TemplateView):
    template_name = 'userprofile/referral_detailed.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_referral,_ = Referral.objects.get_or_create(user=self.request.user)
        referrals = ReferralUsage.objects.filter(referrer=user_referral)
        total_refer_count = ReferralUsage.objects.filter(referrer=user_referral,is_reward_credited=True).count()
        total_rewards = ReferralUsage.objects.filter(referrer=user_referral).aggregate(total_reward=Sum('referral_reward'))
        
        context['total_refer_count'] = total_refer_count
        context['total_rewards'] = total_rewards['total_reward']
        context['referrals'] = referrals
        return context
    