import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import F,Sum
from django.db import transaction
from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods

from .models import *
from userFolder.wallet.models import *
from userFolder.userprofile.views import SecureUserMixin

REFERRAL_REWARD = Decimal('49')

@require_http_methods(["GET", "POST"])
def referral_view(request):
    if not request.user.is_authenticated:
        return redirect('signup')
    
    user = request.user
    if ReferralUsage.objects.filter(receiver=user).exists():
        return redirect('Home_page_user')
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status":'error',"message":"Invalid request data"})
        
        referral_code = data.get('referral_code')
        if not referral_code:
            return JsonResponse({'status': 'error','message': 'Referral code is required'})
        
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
                    referral_reward=REFERRAL_REWARD,
                    status=ReferralUsage.Status.ACTIVE,
                    is_reward_credited=False
                )

                # REFERRER WALLET 
                referrer_wallet, _ = Wallet.objects.get_or_create(user=referral.user)
                Wallet.objects.filter(pk=referrer_wallet.pk).update(
                    balance=F('balance') + REFERRAL_REWARD
                )

                Transaction.objects.create(
                    wallet=referrer_wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=REFERRAL_REWARD,
                    description=f"{user.first_name} used your referral code",
                    status=TransactionStatus.COMPLETED
                )

                # Current user waller WALLET 
                receiver_wallet, _ = Wallet.objects.get_or_create(user=user)
                Wallet.objects.filter(pk=receiver_wallet.pk).update(
                    balance=F('balance') + REFERRAL_REWARD
                )

                Transaction.objects.create(
                    wallet=receiver_wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=REFERRAL_REWARD,
                    description=f"Referral bonus from {referral.user.first_name}",
                    status=TransactionStatus.COMPLETED
                )

                # Update referral usage
                referral_usage.is_reward_credited = True
                referral_usage.status = ReferralUsage.Status.REWARDED
                referral_usage.save()

                # Increment referral count
                Referral.objects.filter(pk=referral.pk).update(
                    used_count=F('used_count') + 1
                )

            return JsonResponse({
                'status': 'success',
                'message': 'Referral applied successfully',
                'reward': str(REFERRAL_REWARD)
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong. Please try again later.'
            })

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
    