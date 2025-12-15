from django.shortcuts import render
from .models import Offer,DiscountType,OfferUsage
from django.http import JsonResponse
from products.models import Product,Category

def offers_view(request):
    offers = Offer.objects.all() 
    total_active_offers = offers.filter(active=True).count() 
    offers_used = OfferUsage.objects.filter(is_active=True).count()
    print(total_active_offers)
    

    context={
        'offers' : offers,
        'total_active_offers':total_active_offers,
        'DiscountType' : DiscountType ,
        'offers_used' : offers_used
    }
    return render(request, 'offer_coupons/offer_coupons.html',context)

def manage_offer_view(request):
    return render(request, 'offer_coupons/manage_offer.html')
    
    
def search_products(request):
    products_search_value = request.GET.get('search','')
    print(products_search_value)
    
    products = Product.objects.filter(name__icontains=products_search_value)[:10]
    
    return JsonResponse([{"id":product.id ,"name":product.name,"image":product.image.url} for product in products],safe=False)

def search_category(request):
    category_search_value = request.GET.get('search','')
    categorys = Category.objects.filter(name__icontains=category_search_value).prefetch_related()[:10]
    
    return JsonResponse([{"id":category.id ,"name":category.name} for category in categorys],safe=False)