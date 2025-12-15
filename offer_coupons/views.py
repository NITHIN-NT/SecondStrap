from django.shortcuts import render
from .models import Offer,DiscountType

def offers_view(request):
    offers = Offer.objects.all() 
    total_active_offers = offers.filter(active=True).count() 
    

    context={
        'offers' : offers,
        'total_active_offers':total_active_offers,
        'DiscountType' : DiscountType
    }
    return render(request, 'offer_coupons/offer_coupons.html',context)

def manage_offer_view(request):
    return render(request, 'offer_coupons/manage_offer.html')
    