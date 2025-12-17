import json
from django.shortcuts import render,redirect,get_object_or_404
from .models import Offer,DiscountType,OfferUsage
from django.http import JsonResponse
from products.models import Product,Category
from .forms import OfferForm
from django.contrib import messages
from django.views.generic import DetailView
from Admin.decorators import superuser_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.views.decorators.http import require_POST

@superuser_required
def offers_view(request):
    offers = Offer.objects.all() 
    total_active_offers = offers.filter(active=True).count() 
    
    context={
        'offers' : offers,
        'total_active_offers':total_active_offers,
        'DiscountType' : DiscountType ,
    }
    return render(request, 'offer_coupons/offer_coupons.html',context)

@superuser_required
@transaction.atomic
def manage_offer_view(request,pk=None):
    instance = get_object_or_404(Offer,pk=pk) if pk else None
    if request.method == 'POST':
        form = OfferForm(request.POST,instance=instance)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.save()
            
            product_ids = request.POST.get('products','').strip(',')
            if product_ids :
                offer.products.set(product_ids.split(','))
            else:
                offer.products.clear()
                
            category_ids = request.POST.get('categories', '').strip(',')
            if category_ids:
                offer.categories.set(category_ids.split(','))
            else:
                offer.categories.clear()
            form.save_m2m()
            verb = "updated" if instance else "created"
            messages.success(request, f'Offer {verb} successfully!')
            return redirect('offers_view')
    else:
        form = OfferForm(instance=instance)
    context = {
        'form' : form,
        'instance' : instance
    }
    return render(request, 'offer_coupons/manage_offer.html',context) 
    
@superuser_required
def search_products(request):
    products_search_value = request.GET.get('search','')

    products = Product.objects.filter(name__icontains=products_search_value)[:10]
    
    return JsonResponse([{"id":product.id ,"name":product.name,"image":product.image.url} for product in products],safe=False)

@superuser_required
def search_category(request):
    category_search_value = request.GET.get('search','')
    categorys = Category.objects.filter(name__icontains=category_search_value).prefetch_related()[:10]
    
    return JsonResponse([{"id":category.id ,"name":category.name} for category in categorys],safe=False)

@method_decorator([never_cache, superuser_required], name="dispatch")
class OfferDetailedView(LoginRequiredMixin,DetailView):
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
                        "current_price" : variant.get_offer_price(offer),
                    })
            
        context['variants_with_price'] = variants_with_price
        context["offer_user"] =  OfferUsage.objects.filter(offer=offer,is_active=True).count()
        return context
 
@superuser_required  
@require_POST
@transaction.atomic
def delete_offer_view(request):
    try:
        data = json.loads(request.body)
        offer_id = data.get('id')
        print(offer_id)
        
        if not offer_id:
            return JsonResponse({"status": "error", "message": "ID is missing"}, status=400)
        
        offer = get_object_or_404(Offer, pk=offer_id)
        offer.delete()
        
        return JsonResponse({"status": "success", "message": "Offer deleted successfully"})
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Something Wen Wrong"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)