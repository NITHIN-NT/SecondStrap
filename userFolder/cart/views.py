import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from .models import *
from products.models import *
# Create your views here.
class CartView(ListView):
    template_name = 'cart/cart.html'
    context_object_name = 'cartitems'

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return CartItems.objects.none()
        
        cart,created = Cart.objects.get_or_create(user=user)
        return  cart.items.select_related('variant__product').order_by('-item_added')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.request.user.cart

        context['total_price'] = cart.total_price
        context['total_quantity'] = cart.total_quantity

        return context

@login_required
def cart_item_add(request): 
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        size = data.get('size')
        quantity = data.get('quantity')

        product = get_object_or_404(Product,id=product_id)
        variant = get_object_or_404(ProductVariant,product=product,size__size=size)
        print('hello')
        cart,_ = Cart.objects.get_or_create(user=request.user)
        item,created = CartItems.objects.get_or_create(
            cart=cart,
            variant=variant,    
            size=size.strip(),
            defaults={"quantity":quantity}
        )
        if not created:
            item.quantity += quantity
        item.save()
        return JsonResponse({'status':'success','message':'success'})

def cart_item_remove(req):
    pass