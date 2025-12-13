import json
import razorpay
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.generic import TemplateView
from .models import Wallet,Transaction
from userFolder.userprofile.views import SecureUserMixin
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import transaction
from django.db.models import F
# Create your views here.
class ProfileWalletView(SecureUserMixin, TemplateView):
    template_name = "wallet/wallet.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        user_wallet = Wallet.objects.select_related('user').prefetch_related('transactions').get(user=self.request.user)
        context['wallet'] = user_wallet
        return context

@require_POST
@login_required(login_url='login')
def create_wallet_razorpay_order(request):
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        amount = Decimal(str(amount))
        
    except json.JSONDecodeError:
        return JsonResponse({"status":"error","message":"Amount not get here!"})
    
    MIN_AMOUNT = Decimal('100.00')
    if amount < MIN_AMOUNT:
        return JsonResponse({"success": False, "error": f"Amount should be greater than or equal to ₹{MIN_AMOUNT}."})
    
    user =request.user
    
    wallet = get_object_or_404(Wallet,user=user)
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
        amount_paise = int(amount * 100)
        
        data = {
            "amount": amount_paise,
            "currency" : settings.RAZORPAY_CURRENCY,
            "payment_capture" : 1,
        }

        razorpay_order = client.order.create(data=data)
    except Exception as e:
        print(f"Razorpay Order Creation Error: {e}")
        return JsonResponse({"success": False, "error": "Failed to communicate with payment gateway."})
    
    request.session['pending_payment'] ={
        'razorpay_order_id': razorpay_order['id'],
        'amount': str(amount),
        'wallet_id': wallet.id,
    }
    
    return JsonResponse({
        "success": True,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount_paise": amount_paise,
        "amount_display": str(amount),
        "currency": settings.RAZORPAY_CURRENCY,
        "user_name":  user.first_name,
        "user_email": user.email,
        "user_phone": getattr(user, 'phone', '9999999999'), 
    })

@csrf_exempt
@never_cache
@login_required(login_url='login')
@require_POST
def wallet_razorpay_callback(request):
    user = request.user
    session_data = request.session.get('pending_payment',None)
    
    if not session_data :
        return JsonResponse({"status":"error","message":"session expired !"})
    
    razorpay_order_id_session = session_data['razorpay_order_id']
    amount_session = Decimal(session_data['amount'])
    wallet_id = session_data['wallet_id']
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST 
    
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")
    
    if razorpay_order_id != razorpay_order_id_session:
        return JsonResponse({"status":"error","message":"Payment verification failed (Order ID mismatch)."})
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status":"error", "message":"Payment verification failed. Invalid signature."})
    
    try:
        with transaction.atomic():
            Wallet.objects.filter(id=wallet_id).update(balance=F('balance')+ amount_session)
            
            wallet = get_object_or_404(Wallet, id=wallet_id)
            
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='CR',
                amount = amount_session,
                description=f"Wallet Top-up via RazorPay.",
                status = "COMP", 
                payment_id=razorpay_payment_id
            )
            
            return JsonResponse({"status":"success","message":"Amount successfully added to the wallet and verified."})            
            request.session.pop('pending_payment', None)

            
    except Exception as e:
        print(f"Razorpay Wallet Update Error: {e}")
        return JsonResponse({"status":"error", "message":"Payment verified, but failed to update wallet balance due to a server error. Please contact support."})