from django.shortcuts import render

def offers_view(request):
    return render(request, 'offer_coupons/offer_coupons.html')

def manage_offer_view(request):
    return render(request, 'offer_coupons/manage_offer.html')
    