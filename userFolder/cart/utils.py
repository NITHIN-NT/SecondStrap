from django.db.models.functions import Coalesce,Greatest
from django.db.models import F,Q,Value,Case,When,DecimalField,ExpressionWrapper
from offer.selectors import get_active_offer_subqueries_cart
from .models import *
from django.http import JsonResponse

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
    )

def verification_requried(view_func):
    def wrapper(request,*args,**kwargs):
        if request.user and not request.user.is_verified:
            return JsonResponse({"message":"Your account is not verified,Verify in the profile section to continue"},status=400)
        return view_func(request,*args,**kwargs)
    return wrapper