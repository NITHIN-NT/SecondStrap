from django.shortcuts import render, redirect
from userFolder.userprofile.models import *
from userFolder.cart.models import *
from django.views.generic import View
from django.http import JsonResponse
from django.contrib import messages


# # Create your views here.
# def checkout_view(request):
#     if request.method == "POST":
#         cart_items = CartItems.objects.prefetch_related("variant").filter(
#             cart__user=request.user
#         )

#         if cart_items:
#             for item in cart_items:
#                 print(item.variant.stock)
#                 if int(item.variant.stock) < 0:
#                     return
#     addresses = Address.objects.filter(user=request.user)
#     context = {"addresses": addresses}
#     return render(request, "checkout/checkout.html", context)


class CheckOutView(View):
    def get(self, request, *args, **kwargs):
        cart_items = CartItems.objects.prefetch_related("variant").filter(
            cart__user=request.user
        )
        if cart_items.exists():
            for item in cart_items:
                if int(item.variant.stock) <= 0:
                    messages.error(request,"Remove the out-of-stock product from the cart to proceed",)
                    return redirect("cart")
        
            addressess = Address.objects.filter(user=request.user)
        else:
            return redirect("products_page_user")
        
        context = {
            "cart_items" : cart_items,
            "addresses" : addressess
        }
        return render(request, "checkout/checkout.html",context)
