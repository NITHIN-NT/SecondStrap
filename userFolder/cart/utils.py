from django.db.models.functions import Coalesce,Greatest
from django.db.models import F,Q,Value,Case,When,DecimalField,ExpressionWrapper
from offer.selectors import get_active_offer_subqueries_cart
from .models import *
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages

def get_annotated_cart_items(user):
    
    product_offer_subquery, category_offer_subquery = get_active_offer_subqueries_cart()
    return CartItems.objects.filter(
        cart__user=user
    ).select_related(
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
                then=Greatest(
                    ExpressionWrapper(
                        F('product_base_price') - (F('product_base_price') * F('best_discount') / Value(100.0)),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    ),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                )
            ),
            When(
                Q(product_offer_price__isnull=False),
                then=F('product_offer_price'),
            ),
            default=F('product_base_price'),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        
        actual_discount = Case(
            When(
                Q(best_discount__gt=0),
                then=ExpressionWrapper(
                    F('product_base_price') * F('best_discount') / Value(100.0),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            When(
                Q(product_offer_price__isnull=False),
                then=ExpressionWrapper(
                    F('product_base_price') - F('product_offer_price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            default=Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),
        
        # Calculate line total (final_price * quantity)
        product_total=ExpressionWrapper(
            F('final_price') * F('quantity'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ),

        subtotal = ExpressionWrapper(
            F('product_base_price') * F('quantity'),
            output_field = DecimalField(max_digits=10, decimal_places=2)
        )
    )

def verification_requried(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if request.user.is_authenticated and not request.user.is_verified:
            msg = "Your account is not verified. Please verify your account in the profile section to continue."

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": msg}, status=403)

            messages.error(request, msg)
            return redirect("cart")

        return view_func(request, *args, **kwargs)

    return wrapper