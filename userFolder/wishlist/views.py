import json
from django.shortcuts import render,redirect
from django.shortcuts import get_object_or_404
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_POST
from products.models import ProductVariant
from .models import Wishlist,WishlistItem
from userFolder.cart.models import Cart,CartItems
from django.contrib.auth.decorators import login_required
from django.db import transaction
from userFolder.cart.utils import verification_requried

# Create your views here.
@verification_requried
def wishlistView(request):
    wishlist_items = None
    if request.user.is_authenticated:    
        wishlist,_ = Wishlist.objects.get_or_create(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product','variant').order_by('-item_added')
    context = {
        'wishlist_items':wishlist_items
    }
    return render(request,'wishlist/wishlist.html',context)

@require_POST
@verification_requried
def add_to_wishlist(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"message": "Please log in to add items to your wishlist."},
            status=401
        )
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
    except json.JSONDecodeError:
        variant_id = None
        return JsonResponse({"status":"error","message":"ID is missing"})
    
    if not variant_id:
        return JsonResponse({"status" : "error","message":"Variant ID missing"},status = 400)
    
    variant = get_object_or_404(ProductVariant,id=variant_id)
    product = variant.product
    
    if not product.is_active:
        return JsonResponse({"status":"error","message":"Sorry. Not Available"},status=400) 
    
    if not variant.stock > 0:
        return JsonResponse({"status":"error","message":"Sorry. Out of stock"},status=400)  
    
    cart,_ = Cart.objects.get_or_create(user=request.user)
    productExists = CartItems.objects.filter(cart=cart,variant=variant).exists()
    
    if productExists:
        return JsonResponse({"status":"error","message":"Item already in the cart !!"},status=208)
    
    wishlist ,new= Wishlist.objects.get_or_create(user=request.user)

    wishlist_item,created = WishlistItem.objects.get_or_create(
        wishlist = wishlist,
        product = variant.product,
        variant = variant
    )

    product.in_wishlist = True
    product.save()
    
    if created:
        return JsonResponse({"status":"success","message":"Item Added to the wishlist",},status=200)
    else:
        return JsonResponse({"status":"error","message":"Item already in the wishlist",},status=400)
    
@require_POST
@verification_requried
def add_to_cart(request):
    try:
        data = json.loads(request.body)
        variant_id =data.get('variant_id')
        size = data.get('size')
    except json.JSONDecodeError:
        return JsonResponse({"status":"error","message":"Data is not here"})
    
    if not variant_id:
        return JsonResponse({"status":"error","message":"Variant Id is missing."})
    
    variant = get_object_or_404(ProductVariant,id=variant_id)
    
    if not variant.stock > 0:
        return JsonResponse({"status":"error","message":"Sorry. Out of stock"})
    
    if not variant.product.is_active:
        return JsonResponse({"status":"error","message":"Sorry. Not Available"})
    
    cart,_ = Cart.objects.get_or_create(user=request.user)
    
    productExists = CartItems.objects.filter(cart=cart,variant=variant).exists()
    
    if not productExists:
        CartItems.objects.create(
            cart=cart,
            variant=variant,
            size=size,
            from_wishlist = True
        )
        wishlist_item = WishlistItem.objects.get(variant=variant)
        wishlist_item.delete()
        return JsonResponse({"status":"success","message":"Item moved to the cart"})
    else:
        return JsonResponse({"status":"error","message":"Item already in the cart"})
    
@require_POST
@verification_requried
@transaction.atomic
def remove_from_wishlist(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        variant_id = data.get('variant_id')
        
        if not item_id and not variant_id:
            return JsonResponse({
                "status": "error", 
                "message": "Item ID or Variant ID is required"
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error", 
            "message": "Invalid data"
        }, status=400)
    
    try:
        if item_id:
            item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
        elif variant_id:
            item = get_object_or_404(
                WishlistItem, 
                variant_id=variant_id, 
                wishlist__user=request.user
            )
        
        item.product.in_wishlist = False
        item.product.save()
        item.delete()
        return JsonResponse({
            "status": "success", 
            "message": "Item removed from the wishlist!"
        })
        
    except Exception as e:
        print(str(e))
        return JsonResponse({
            "status": "error", 
            "message": "Something went wrong"
        }, status=500)