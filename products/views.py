from django.shortcuts import render
from .models import Product, ProductImage, Category
from django.utils import timezone
from datetime import date, timedelta
from django.core.paginator import Paginator
from django.db.models import Max, Min
from django.views.generic import TemplateView, DetailView, ListView
from django.db.models import Min, Max, Sum
from django.db.models.functions import Coalesce

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


class HomePageView(TemplateView):
    template_name = "products/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        products = (
            Product.objects.select_related("category")
            .prefetch_related("variants")
            .filter(is_active=True)
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        featured_products = (
            Product.objects.filter(is_featured=True, is_active=True)
            .prefetch_related("variants")
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        most_demanded = (
            Product.objects.filter(is_most_demanded=True, is_active=True)
            .prefetch_related("variants")
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        today = timezone.now().date()
        new_arrivals = (
            Product.objects.filter(created_at__date=today, is_active=True)
            .prefetch_related("variants")
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )

        categories = Category.objects.filter(is_active=True).prefetch_related(
            "products"
        )[:4]
        categories_for_template = []
        for category in categories:
            product = category.products.filter(
                is_active=True, image__isnull=False
            ).first()
            if product:
                categories_for_template.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "image": product.image,
                        "alt_text": product.name,
                    }
                )

        context["products"] = products
        context["featured_products"] = featured_products
        context["most_demanded"] = most_demanded
        context["new_arrivals"] = new_arrivals
        context["categories_for_template"] = categories_for_template

        return context


class AboutView(TemplateView):
    template_name = "products/about.html"


def product_list_view(request):
    categories = Category.objects.filter(is_active=True).order_by("name")
    products = (
        Product.objects.filter(is_active=True)
        .prefetch_related("variants")
        .annotate(
            offer_price=Min("variants__offer_price"),
            total_stock=Coalesce(
                Sum("variants__stock"), 0
            ),  # Coalesce is a database function in Django used to
            # replace NULL values with a default value (usually 0 or an empty string).
        )
        .order_by("?")
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
        products = products.order_by("variants__offer_price")
    elif selected_sort == "price-high-low":
        products = products.order_by("-variants__offer_price")
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
            products = products.filter(variants__offer_price__lte=price_limit)
        except ValueError:
            pass

    # Search Filter
    if search:
        products = products.filter(name__icontains=search)

    # Price Range
    price_range = Product.objects.filter(is_active=True).aggregate(
        min_amount=Min("variants__offer_price"), max_amount=Max("variants__offer_price")
    )

    # Pagination
    paginator = Paginator(products, 9)
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
        query_set = super().get_queryset()
        return (
            query_set.filter(is_active=True)
            .select_related("category")
            .prefetch_related("variants__size", "images")
            .annotate(
                offer_price=Min("variants__offer_price"),
                base_price=Min("variants__base_price"),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        all_images = product.images.all()
        context["images_list_limited"] = all_images[:4]
        context["sizes"] = product.variants.all()
        product_category = product.category

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

        return context
