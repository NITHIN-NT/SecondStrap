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
from django.contrib.auth.decorators import login_required
from django.db import transaction
from offer.selectors import get_active_offer_subqueries_cart
from django.db.models.functions import Coalesce,Greatest
from django.db.models import Value,F,Q,DecimalField,Case,When,ExpressionWrapper
# Create your views here.
class CartView(LoginRequiredMixin, ListView):
    template_name = "cart/cart.html"
    context_object_name = "cartitems"
    login_url = "login"

    def get_queryset(self):
        user = self.request.user

        cart, created = Cart.objects.get_or_create(user=user)
        
        product_offer_subquery, category_offer_subquery = get_active_offer_subqueries_cart()

        return cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
            "variant__size"
        ).annotate(
            product_base_price = F('variant__base_price'),
            product_offer_price =F('variant__offer_price'),
            
            offer_prod_val=Coalesce(product_offer_subquery, Value(0, output_field=DecimalField())),
            offer_cat_val=Coalesce(category_offer_subquery, Value(0, output_field=DecimalField())),
            
            best_discount = Greatest("offer_prod_val","offer_cat_val"),
            
            final_price = Case(
                When(
                    Q(best_discount__gt=0),
                    then=F('product_base_price') - F('best_discount'),
                ),
                When(
                    Q(product_offer_price__isnull=False),
                    then=F('product_offer_price'),
                ),
                default=F('product_offer_price'),
                output_field=DecimalField(),
            ),
            
            actual_discount = Case(
                When(
                    Q(best_discount__gt=0),
                    then=F('best_discount')
                ),
                When(
                    Q(product_offer_price__isnull=False),
                    then=F('product_base_price') - F('product_offer_price')
                ),
                default=F('product_base_price'),
                output_field=DecimalField()
            ),
            
            # Calculate line total (final_price * quantity)
            product_total=ExpressionWrapper(
                F('final_price') * F('quantity'),
                output_field=DecimalField()
            ),

            subtotal = ExpressionWrapper(
                F('product_base_price') * F('quantity'),
                output_field = DecimalField()
            )
        ).order_by("-item_added")

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
@transaction.atomic
def cart_item_add(request):
    # Check if the user is logged in
    if not request.user.is_authenticated:
        return JsonResponse(
            {"status": "error", "message": "Please log in to add items to your cart."},
            status=401,
        )

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
