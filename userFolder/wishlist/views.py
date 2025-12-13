import json
from django.shortcuts import render,redirect
from django.shortcuts import get_object_or_404
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_POST
from products.models import ProductVariant
from .models import Wishlist,WishlistItem

# Create your views here.
def wishlistView(request):
    wishlist = Wishlist.objects.get(user=request.user)
    wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product','variant').order_by('-item_added')
    context = {
        'wishlist_items':wishlist_items
    }
    return render(request,'wishlist/wishlist.html',context)

@require_POST
def add_to_wishlist(request):
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
    except json.JSONDecodeError:
        variant_id = None
        return JsonResponse({"status":"error","message":"ID is missing"})

    print("Received variant_id:", variant_id)

    if not request.user.is_authenticated:
        return JsonResponse({"status":"error","message":"Login to add items to wishlist"},status=401)
    
    if not variant_id:
        return JsonResponse({"status" : "error","message":"Variant ID missing"},status = 400)
    
    variant = get_object_or_404(ProductVariant,id=variant_id)
    
    
    wishlist ,new= Wishlist.objects.get_or_create(user=request.user)
    
    wishlist_item,created = WishlistItem.objects.get_or_create(
        wishlist = wishlist,
        product = variant.product,
        variant = variant
    )
    
    if created:
        return JsonResponse({"status":"success","message":"Item Added to the wishlist",},status=200)
    else:
        return JsonResponse({"status":"error","message":"Item already in the wishlist",},status=400)
    
        
        