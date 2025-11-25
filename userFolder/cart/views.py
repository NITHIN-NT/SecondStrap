import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from products.models import *
from django.contrib import messages


# Create your views here.
class CartView(LoginRequiredMixin, ListView):
    template_name = "cart/cart.html"
    context_object_name = "cartitems"
    login_url = "login"

    def get_queryset(self):
        user = self.request.user

        cart, created = Cart.objects.get_or_create(user=user)
        return cart.items.select_related("variant__product").order_by("-item_added")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.request.user.cart

        context["total_price"] = cart.total_price
        context["total_quantity"] = cart.total_quantity

        return context


def cart_item_add(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid request method."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"status": "error", "message": "Please log in to add items to your cart."},
            status=401,
        )

    try:
        data = json.loads(request.body)
        product_id = data.get("product_id")
        size = data.get("size")
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {"status": "error", "message": "Invalid data sent."}, status=400
        )

    product = get_object_or_404(Product, id=product_id)

    variant = get_object_or_404(ProductVariant, product=product, size__size=size)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItems.objects.get_or_create(
        cart=cart, variant=variant, size=size.strip(), defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
    item.save()
    return JsonResponse({"status": "success", "message": "Item added to cart !!"})


def cart_item_remove(req):
    pass
