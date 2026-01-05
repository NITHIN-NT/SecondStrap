from django.shortcuts import render
from .models import Product, ProductVariant, Category
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Max, Min
from django.views.generic import TemplateView, DetailView
from django.db.models import Min, Max, Sum, Count
from django.db.models.functions import Coalesce
from offer.models import Offer
from django.http import JsonResponse
from django.db.models import OuterRef,Subquery,F,Value,DecimalField,When,Case,Prefetch,Q
from django.db.models.functions import Coalesce, Greatest
from offer.models import OfferType
from offer.selectors import get_active_offer_subqueries
from coupon.models import Coupon
from userFolder.review.models import Review
from django.db.models import Avg
# Create your views here.
"""
def home_page_view(request):
    products = Product.objects.select_related('category').order_by('?')[:4]
    featured_products = Product.objects.filter(is_featured=True).order_by('?')[:4]
    most_demanded = Product.objects.filter(is_most_demanded=True).order_by('?')[:4]
    today = timezone.now().date()
    new_arrivals = Product.objects.filter(created_at__date=today).order_by('?')[:4]
    context = {
        'products' : products,
        'featured_products' : featured_products,
        'most_demanded' : most_demanded,
        'new_arrivals' : new_arrivals
    }
    return render(request,'products/home.html',context)
"""



def product_list_view(request):
    categories = (
        Category.objects.filter(
            is_active=True,
        )
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
            total_stock=Coalesce(
                Sum("variants__stock"), 0
            ),  # Coalesce is a database function in Django used to
            # replace NULL values with a default value (usually 0 or an empty string).
        )
        .order_by("?")
    )
    
    # Here we are just calling the function because i need all the products offers
    product_offer_subquery, category_offer_subquery = get_active_offer_subqueries()
    
    products = products.annotate(
        min_variant_price=Min("variants__base_price"),
        offer_prod_val=Coalesce(product_offer_subquery, Value(0, output_field=DecimalField())),
        offer_cat_val=Coalesce(category_offer_subquery, Value(0, output_field=DecimalField())),
    ).annotate(
        best_discount=Greatest('offer_prod_val', 'offer_cat_val'),
    ).annotate(
        min_discounted_price=Greatest(F('min_variant_price') - F('best_discount'),
        Value(0), output_field=DecimalField(max_digits=10, decimal_places=2))
    )

    # Query Params
    selected_category_id = request.GET.get("category")
    selected_price = request.GET.get("price_range")
    selected_sort = request.GET.get("sort")
    search = request.GET.get("search")

    # Sorting
    if selected_sort == "newest":
        products = products.order_by("-created_at")
    elif selected_sort == "price-low-high":
        products = products.order_by("min_variant_price")
    elif selected_sort == "price-high-low":
        products = products.order_by("-min_variant_price")
    elif selected_sort == "name-asc":
        products = products.order_by("name")
    elif selected_sort == "name-desc":
        products = products.order_by("-name")
    elif selected_sort == "featured":
        products = products.order_by("-is_featured", "-created_at")

    # Category Filter
    if selected_category_id and selected_category_id != "all":
        products = products.filter(category__id=selected_category_id)

    # Price Filter
    if selected_price:
        try:
            price_limit = float(selected_price)
            products = products.filter(min_variant_price__lte=price_limit).distinct()
        except ValueError:
            pass

    # Search Filter
    if search:
        products = products.filter(name__icontains=search).distinct()

    # Price Range
    price_range = Product.objects.filter(is_active=True).aggregate(
        min_amount=Min("variants__offer_price"), max_amount=Max("variants__offer_price")
    )

    # Pagination
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
            product_ref='product',
            category_ref='product__category'
        )

        variants_queryset = ProductVariant.objects.annotate(
            offer_prod_value=Coalesce(
                Subquery(product_offer_subquery), 
                Value(0, output_field=DecimalField())
            ),
            offer_cate_value=Coalesce(
                Subquery(category_offer_subquery), 
                Value(0, output_field=DecimalField())
            )
        ).annotate(
            best_discount=Greatest('offer_prod_value', 'offer_cate_value'),
        ).annotate(
            # Calculate discount from offer_price if it exists, otherwise from base_price
            discounted_price=Case(
                When(
                    Q(best_discount__gt=0),
                    then=F('base_price') - F('best_discount')
                ),
                When(
                    Q(offer_price__isnull=False),
                    then=F('offer_price')
                ),
                default=F('base_price'),
                output_field=DecimalField()
            ),
            # Calculate actual discount amount
            actual_discount=Case(
                When(
                    Q(best_discount__gt=0),
                    then=F('best_discount')
                ),
                When(
                    Q(offer_price__isnull=False),
                    then=F('base_price') - F('offer_price')
                ),
                default=Value(0),
                output_field=DecimalField()
            )
        )
        
        return (
            Product.objects.filter(is_active=True)
            .annotate(base_price=Min("variants__base_price"))
            .select_related('category')
            .prefetch_related(
                Prefetch("variants", queryset=variants_queryset, to_attr="annotated_variants"),
                "images"
            )
        )
        
        # the to_attr is store the data in a new list on the product object called annotated_variants

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        all_images = product.images.all()
        context["images_list_limited"] = all_images[:4]
        context["sizes"] = product.annotated_variants
        product_category = product.category
        reviews = Review.objects.filter(product=product)
        avg_rating = Review.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg'] or 0
        ratings = reviews.count()
        
        rating_range = range(int(avg_rating))
        
        for review in reviews:
            review.filled_stars = range(review.rating)
            review.empty_stars = range(5-review.rating)
        
        
        now = timezone.now()
        coupons = Coupon.objects.filter(start_date__lte=now,end_date__gte=now,is_active=True)

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
        context['reviews'] = reviews
        context['avg_rating'] = avg_rating 
        context['rating_range'] = rating_range
        context['ratings'] = ratings
        return context


'''
OuterRef = To make a field from the main query available inside a Subquery expression.
'''