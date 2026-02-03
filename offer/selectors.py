from .models import Offer,OfferType
from django.db.models import OuterRef
from django.utils import timezone

def get_active_offer_subqueries(product_ref='id', category_ref='category'):
    # Subquery to find the products offer
    now = timezone.now()
    
    product_offer_subquery = Offer.objects.filter(
        products=OuterRef(product_ref),       
        offer_type=OfferType.PRODUCT,
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-discount_percentage').values('discount_percentage')[:1]

    category_offer_subquery = Offer.objects.filter(
        categories=OuterRef(category_ref),
        offer_type=OfferType.CATEGORY,
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-discount_percentage').values('discount_percentage')[:1]
    
    return product_offer_subquery, category_offer_subquery


def get_active_offer_subqueries_cart(
    product_ref='variant__product_id',
    category_ref='variant__product__category_id'
):
    now = timezone.now()

    product_offer_subquery = (
        Offer.objects.filter(
            products=OuterRef(product_ref),
            offer_type=OfferType.PRODUCT,
            active=True,
            start_date__lte=now,
            end_date__gte=now,
        )
        .order_by('-discount_percentage')
        .values('discount_percentage')[:1]
    )

    category_offer_subquery = (
        Offer.objects.filter(
            categories=OuterRef(category_ref),
            offer_type=OfferType.CATEGORY,
            active=True,
            start_date__lte=now,
            end_date__gte=now,
        )
        .order_by('-discount_percentage')
        .values('discount_percentage')[:1]
    )

    return product_offer_subquery, category_offer_subquery