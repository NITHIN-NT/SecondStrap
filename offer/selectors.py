from .models import Offer,OfferType
from django.db.models import OuterRef, Q
from django.utils import timezone

def get_active_offer_subqueries(product_ref="id", category_ref="category_id"):
    now = timezone.now()

    product_offer_subquery = Offer.objects.filter(
        products__id=OuterRef(product_ref),   # ✅ important change
        offer_type=OfferType.PRODUCT,
        active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-discount_percentage').values('discount_percentage')[:1]

    category_offer_subquery = Offer.objects.filter(
        categories__id=OuterRef(category_ref),  # ✅ important change
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
            products__id=OuterRef(product_ref),
            offer_type=OfferType.PRODUCT,
            active=True,
            start_date__lte=now,
        )
        .filter(Q(end_date__gte=now) | Q(end_date__isnull=True))
        .order_by('-discount_percentage')
        .values('discount_percentage')[:1]
    )

    category_offer_subquery = (
        Offer.objects.filter(
            categories__id=OuterRef(category_ref),
            offer_type=OfferType.CATEGORY,
            active=True,
            start_date__lte=now,
        )
        .filter(Q(end_date__gte=now) | Q(end_date__isnull=True))
        .order_by('-discount_percentage')
        .values('discount_percentage')[:1]
    )

    return product_offer_subquery, category_offer_subquery