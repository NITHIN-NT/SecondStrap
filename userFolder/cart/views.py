import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from products.models import *
from django.views.decorators.http import require_POST
from django.db import transaction
from .utils import get_annotated_cart_items,verification_required
from django.contrib.auth.decorators import login_required
# Create your views here.
class CartView(LoginRequiredMixin, ListView):
    template_name = "cart/cart.html"
    context_object_name = "cartitems"
    login_url = "login"

    def get_queryset(self):
        user = self.request.user

        cart, created = Cart.objects.get_or_create(user=user)

        return get_annotated_cart_items(self.request.user).order_by("-item_added")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart, created = Cart.objects.get_or_create(user=self.request.user)     
        cartitems = context['cartitems']   
        

        context["subtotal"] = sum(item.subtotal for item in cartitems)
        context["total_price"] = sum(item.product_total for item in cartitems)
        context["total_quantity"] = cart.total_quantity
        context["total_savings"] = sum((item.actual_discount for item in cartitems))

        return context

@require_POST
@verification_required
@transaction.atomic
def cart_item_add(request):

    # JSON data from the request body
    try:
        data = json.loads(request.body)
        product_id = data.get("product_id")
        size = data.get("size")
        quantity = int(data.get("quantity", 1))  # Default quantity = 1
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {"status": "error", "message": "Invalid data sent."},
            status=400,
        )

    # Ensure product ID is provided
    if not product_id:
        return JsonResponse(
            {"status": "error", "message": "Invalid data sent."},
            status=400,
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

    # check the price if there is any discount available or not.
    
    # Get or create the user's cart
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Get or create the cart item for the chosen variant
    item, created = CartItems.objects.get_or_create(cart=cart,variant=variant,size=cleaned_size,defaults={"quantity": quantity})

    # If the item already exists, increase the quantity
    if not created:
        new_quantity = item.quantity + quantity

        # Prevent adding more than available stock
        if new_quantity > variant.stock:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Cannot add more than {variant.stock} item(s) to cart.",
                },
                status=400,
            )

        item.quantity = new_quantity
        item.save()

    # Success response
    return JsonResponse({"status": "success", "message": "Item added to cart !!"})


@require_POST
@verification_required
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


@require_POST
@verification_required
def update_cart_item_quantity(request):
    # Getting the data
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    # Collecting the details from the items
    item_id = data.get("item_id")
    quantity = data.get("quantity")

    if not item_id:
        return JsonResponse(
            {"status": "error", "message": "Item not found !!"}, status=400
        )

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "error", "message": "Invalid quantity"}, status=400
        )

    if quantity < 1:
        return JsonResponse(
            {"status": "error", "message": "Quantity must be at least 1"}, status=400
        )

    # Fetching Item form the cart
    try:
        item = CartItems.objects.get(id=item_id)
    except CartItems.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Error found !!!"}, status=404
        )

    current_stock = item.variant.stock or 0

    if quantity > current_stock:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Only {current_stock} items available.",
                "available_stock": current_stock,
            },
            status=400,
        )
    item.quantity = quantity
    item.save()
    return JsonResponse({"status": "success", "message": "Quantity updated"})
