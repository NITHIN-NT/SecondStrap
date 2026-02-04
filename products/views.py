from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.generic import DetailView
from django.http import JsonResponse
from django.db.models import (
    Min, Max, Sum, Count, Avg,
    OuterRef, Subquery, F, Value,
    DecimalField, When, Case, Prefetch, Q,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce, Greatest
from .models import Product, ProductVariant, Category
from offer.selectors import get_active_offer_subqueries
from coupon.models import Coupon
from userFolder.review.models import Review
from offer.models import Offer,OfferType

def product_list_view(request):
    categories = (
        Category.objects.filter(is_active=True)
        .prefetch_related("products")
        .annotate(product_count=Count("products"))
        .order_by("name")
    )

    products = (
        Product.objects.filter(is_active=True)
        .prefetch_related("variants")
        .annotate(
            offer_price=Min("variants__offer_price"),
            base_price=Min("variants__base_price"),
            stock=Coalesce(Min("variants__stock"), 0),
            total_stock=Coalesce(Sum("variants__stock"), 0),
        )
        .order_by("?")
    )

    product_offer_subquery, category_offer_subquery = get_active_offer_subqueries(
        product_ref="id",
        category_ref="category_id",
    )

    # ✅ Apply offers (percentage based)
    products = products.annotate(
        min_variant_price=Min("variants__base_price"),
        min_variant_offer_price=Min("variants__offer_price"),

        offer_prod_val=Coalesce(
            Subquery(product_offer_subquery),
            Value(0, output_field=DecimalField())
        ),
        offer_cat_val=Coalesce(
            Subquery(category_offer_subquery),
            Value(0, output_field=DecimalField())
        ),
    ).annotate(
        best_discount=Greatest("offer_prod_val", "offer_cat_val"),
    ).annotate(
        min_discounted_price=Case(
            When(
                best_discount__gt=0,
                then=Greatest(
                    ExpressionWrapper(
                        F("min_variant_price") - (F("min_variant_price") * F("best_discount") / Value(100.0)),
                        output_field=DecimalField(max_digits=10, decimal_places=2),
                    ),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                )
            ),
            When(
                min_variant_offer_price__isnull=False,
                then=F("min_variant_offer_price")
            ),
            default=F("min_variant_price"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )
    selected_category_id = request.GET.get("category")
    selected_price = request.GET.get("price_range")
    selected_sort = request.GET.get("sort")
    search = request.GET.get("search")

    if selected_sort == "newest":
        products = products.order_by("-created_at")
    elif selected_sort == "price-low-high":
        products = products.order_by("min_discounted_price")
    elif selected_sort == "price-high-low":
        products = products.order_by("-min_discounted_price")
    elif selected_sort == "name-asc":
        products = products.order_by("name")
    elif selected_sort == "name-desc":
        products = products.order_by("-name")
    elif selected_sort == "featured":
        products = products.order_by("-is_featured", "-created_at")

    if selected_category_id and selected_category_id != "all":
        products = products.filter(category_id=selected_category_id)

    if selected_price:
        try:
            price_limit = float(selected_price)
            products = products.filter(min_discounted_price__lte=price_limit).distinct()
        except ValueError:
            pass

    if search:
        products = products.filter(name__icontains=search).distinct()

    price_range = Product.objects.filter(is_active=True).aggregate(
        min_amount=Min("variants__offer_price"),
        max_amount=Max("variants__offer_price"),
    )

    paginator = Paginator(products, 13)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    current_page = page_obj.number
    total_pages = paginator.num_pages
    window = 5
    half_window = (window - 1) // 2

    start_page = max(1, current_page - half_window)
    end_page = min(total_pages, current_page + half_window)

    if current_page <= half_window:
        start_page = 1
        end_page = min(window, total_pages)
    elif current_page >= total_pages - half_window:
        end_page = total_pages
        start_page = max(1, total_pages - window + 1)

    custom_page_range = range(start_page, end_page + 1)

    context = {
        "categories": categories,
        "page_obj": page_obj,
        "custom_page_range": custom_page_range,
        "max_amount": price_range["max_amount"] or 10000,
        "min_amount": price_range["min_amount"] or 0,
        "selected_category_id": selected_category_id,
        "selected_price": selected_price,
        "selected_sort": selected_sort,
        "search": search,
    }

    return render(request, "products/products.html", context)


class ProductDetailedView(DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        product_offer_subquery, category_offer_subquery = get_active_offer_subqueries(
            product_ref="product_id",
            category_ref="product__category_id",
        )

        variants_queryset = (
            ProductVariant.objects.annotate(
                offer_prod_value=Coalesce(
                    Subquery(product_offer_subquery),
                    Value(0, output_field=DecimalField())
                ),
                offer_cate_value=Coalesce(
                    Subquery(category_offer_subquery),
                    Value(0, output_field=DecimalField())
                ),
            )
            .annotate(
                best_discount=Greatest("offer_prod_value", "offer_cate_value"),
            )
            .annotate(
                offer_discount_amount=ExpressionWrapper(
                    F("base_price") * F("best_discount") / Value(100.0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
            .annotate(
                discounted_price=Case(
                    When(
                        best_discount__gt=0,
                        then=Greatest(
                            ExpressionWrapper(
                                F("base_price") - F("offer_discount_amount"),
                                output_field=DecimalField(max_digits=10, decimal_places=2),
                            ),
                            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                        )
                    ),

                    When(
                        offer_price__isnull=False,
                        then=F("offer_price")
                    ),
                    default=F("base_price"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                actual_discount=Case(
                    When(
                        best_discount__gt=0,
                        then=F("offer_discount_amount") 
                    ),
                    When(
                        offer_price__isnull=False,
                        then=Greatest(
                            ExpressionWrapper(
                                F("base_price") - F("offer_price"),
                                output_field=DecimalField(max_digits=10, decimal_places=2),
                            ),
                            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                        )
                    ),
                    default=Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
        )

        return (
            Product.objects.filter(is_active=True)
            .annotate(base_price=Min("variants__base_price"))
            .select_related("category")
            .prefetch_related(
                Prefetch("variants", queryset=variants_queryset, to_attr="annotated_variants"),
                "images",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        all_images = product.images.all()
        context["images_list_limited"] = all_images[:4]
        context["sizes"] = product.annotated_variants

        reviews = Review.objects.filter(product=product)
        avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0
        ratings = reviews.count()
        rating_range = range(int(avg_rating))

        for review in reviews:
            review.filled_stars = range(review.rating)
            review.empty_stars = range(5 - review.rating)

        now = timezone.now()
        coupons = Coupon.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            is_active=True
        )

        related_products = (
            Product.objects.filter(category=product.category, is_active=True)
            .select_related("category")
            .prefetch_related("variants", "images")
            .annotate(
                base_price=Min("variants__base_price"),
                offer_price=Min("variants__offer_price"),
            )
            .exclude(pk=product.pk)
        )
        random_products = (
            Product.objects.filter(is_active=True)
            .exclude(pk=product.pk)
            .prefetch_related("variants", "images")
            .annotate(
                offer_price=Min("variants__offer_price"),
                base_price=Min("variants__base_price"),
            )
            .order_by("?")
        )
        context["related_products"] = related_products[:4]
        context["random_products"] = random_products[:4]
        context["coupons"] = coupons
        context["reviews"] = reviews
        context["avg_rating"] = avg_rating
        context["rating_range"] = rating_range
        context["ratings"] = ratings

        return context