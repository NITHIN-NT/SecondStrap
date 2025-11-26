import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from products.models import *
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.views.decorators.http import require_POST


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
        cart, _ = Cart.objects.get_or_create(user=self.request.user)

        context["total_price"] = cart.total_price
        context["total_quantity"] = cart.total_quantity

        return context


@require_POST
def cart_item_add(request):

    # Check if the user is logged in
    if not request.user.is_authenticated:
        return JsonResponse(
            {"status": "error", "message": "Please log in to add items to your cart."},
            status=401,
        )

    #  JSON data from the request body
    try:
        data = json.loads(request.body)
        product_id = data.get("product_id")
        size = data.get("size")
        quantity = int(data.get("quantity", 1))  # Default quantity = 1
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {"status": "error", "message": "Invalid data sent."}, status=400
        )

    # Ensure product ID is provided
    if not product_id:
        return JsonResponse(
            {"status": "error", "message": "Invalid data sent ."}, status=400
        )

    # Get the product
    product = get_object_or_404(Product, id=product_id)

    # If size is provided, get the corresponding variant
    if size:
        cleaned_size = size.strip()
        variant = get_object_or_404(
            ProductVariant, product=product, size__size=cleaned_size
        )
    else:
        # If no size is provided, pick the first available variant
        variant = ProductVariant.objects.filter(product=product).first()
        if not variant:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "No variants available for this product.",
                },
                status=400,
            )
        cleaned_size = ""
    # Check if enough stock is available
    if variant.stock < quantity:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Only {variant.stock} item(s) available in this size.",
            },
            status=400,
        )

    # Get or create the user's cart
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Get or create the cart item for the chosen variant
    item, created = CartItems.objects.get_or_create(
        cart=cart, variant=variant, size=cleaned_size, defaults={"quantity": quantity}
    )

    # If the item already exists, increase the quantity
    if not created:
        new_quantity = item.quantity + quantity

        # Prevent adding more than available stock
        if new_quantity > variant.stock:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Cannot add more that {variant.stock} item(s) to cart .",
                }
            )

        item.quantity = new_quantity
        item.save()

    # Success response
    return JsonResponse({"status": "success", "message": "Item added to cart !!"})


@require_POST
def cart_item_remove(request):
    data = json.loads(request.body)
    item_id = data.get("item_id")
    if not item_id:
        return JsonResponse({"status": "error", "message": "Item not in cart!!!"})

    try:
        item = CartItems.objects.get(id=item_id, cart__user=request.user)
        item.delete()
        return JsonResponse({"status": "success", "message": "Item removed"})
    except CartItems.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found"})
