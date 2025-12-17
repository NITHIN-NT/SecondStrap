from django.shortcuts import render,redirect
from .models import Offer,DiscountType,OfferUsage
from products.models import ProductVariant
from django.http import JsonResponse
from products.models import Product,Category
from .forms import OfferForm
from django.contrib import messages
from django.views.generic import DetailView

def offers_view(request):
    offers = Offer.objects.all() 
    total_active_offers = offers.filter(active=True).count() 
    offers_used = OfferUsage.objects.filter(is_active=True).count()
    
    context={
        'offers' : offers,
        'total_active_offers':total_active_offers,
        'DiscountType' : DiscountType ,
        'offers_used' : offers_used
    }
    return render(request, 'offer_coupons/offer_coupons.html',context)

def manage_offer_view(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()    
            product_ids = request.POST.get('products','')
            print(product_ids)
            if product_ids :
                offer.products.set(product_ids.split(','))
                
            category_ids = request.POST.get('categories', '')
            if category_ids:
                offer.categories.set(category_ids.split(','))
            
            form.save_m2m()
            messages.success(request,'offer created')
            return redirect('offers_view')
    else:
        form = OfferForm()
    return render(request, 'offer_coupons/manage_offer.html',{'form':form}) 
    
    
def search_products(request):
    products_search_value = request.GET.get('search','')

    products = Product.objects.filter(name__icontains=products_search_value)[:10]
    
    return JsonResponse([{"id":product.id ,"name":product.name,"image":product.image.url} for product in products],safe=False)

def search_category(request):
    category_search_value = request.GET.get('search','')
    categorys = Category.objects.filter(name__icontains=category_search_value).prefetch_related()[:10]
    
    return JsonResponse([{"id":category.id ,"name":category.name} for category in categorys],safe=False)


class OfferDetailedView(DetailView):
    model=Offer
    template_name = 'offer_coupons/offer_detail.html'
    context_object_name = 'offer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offer = self.object
        variants_with_price = []
        for product in offer.products.prefetch_related('variants'):
            for variant in product.variants.all():
                variants_with_price.append({
                        "product" : product,
                        "variant" : variant,
                        "current_price" : variant.get_offer_price(offer)
                    })
            
        context['variants_with_price'] = variants_with_price
        return context
    