from django.shortcuts import redirect,get_object_or_404,render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db import transaction
from django.db.models import Count
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory
from django.contrib import messages

from products.models import Product,Category,ProductVariant,ProductImage
from ..forms import *

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class AdminProductsView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "products/products_admin.html"
    context_object_name = "products"
    ordering = ["-updated_at"]
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("search", "")
        category_query = self.request.GET.get("category", "")
        status_query = self.request.GET.get("status", "")

        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        if category_query:
            queryset = queryset.filter(category__name__icontains=category_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categorys"] = Category.objects.all()
        context["search_query"] = self.request.GET.get("search", "")
        context["category_filter"] = self.request.GET.get("category", "")
        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        context["query_params"] = query_params.urlencode()
        return context

@staff_member_required(login_url='admin_login')
@transaction.atomic
@never_cache
def manage_product(request, id=None):
    """
    This Function is used to Manage Product
    Both add and edit Products is Done by this
    """

    try:
        product = get_object_or_404(Product, id=id) if id else None
    except ValueError:
        product = None
    extra_forms = 1 if product is None else 0
    VariantFormSet = inlineformset_factory(
        Product,
        ProductVariant,
        form=VariantForm,
        extra=extra_forms,
        min_num=1,
        can_delete=True,
        can_delete_extra=True,
    )

    ImageFormSet = inlineformset_factory(
        Product,
        ProductImage,
        form=ImageForm,
        extra=extra_forms,
        min_num=3,
        validate_min=True,
        can_delete=True,
        can_delete_extra=True,
    )
    if request.method == "POST":
        product_form = AdminProductAddForm(
            request.POST, request.FILES, instance=product
        )
        formset = VariantFormSet(request.POST, instance=product, prefix="variants")
        formset_images = ImageFormSet(
            request.POST, request.FILES, instance=product, prefix="images"
        )

        if product_form.is_valid() and formset.is_valid() and formset_images.is_valid():
            product = product_form.save()
            formset.instance = product
            formset.save()
            formset_images.instance = product
            formset_images.save()
            messages.success(
                request,
                f"{product.name} is Added/Edited Successfuly.",
                extra_tags="admin",
            )
            return redirect("admin_products")
        else:
            print("Product Form Errors:", product_form.errors)
            print("Variant Formset Errors:", formset.errors)
            print("Variant Formset Non-Form Errors:", formset.non_form_errors())
            print("Image Formset Errors:", formset_images.errors)
            print("Image Formset Non-Form Errors:", formset_images.non_form_errors())
            messages.error(request, "Please fix the errors below.", extra_tags="admin")
    else:
        product_form = AdminProductAddForm(instance=product)
        formset = VariantFormSet(instance=product, prefix="variants")
        formset_images = ImageFormSet(instance=product, prefix="images")
    context = {
        "product_form": product_form,
        "formset": formset,
        "formset_images": formset_images,
        "product": product,
    }

    return render(request, "products/product_add_edit.html", context)

@staff_member_required(login_url='admin_login')
@transaction.atomic
@never_cache
def toggle_product_block(request, id):
    """
    This Function is used to Block and Unblock Products
    """
    if request.method == "POST":
        product = get_object_or_404(Product, id=id)
        product.is_active = not product.is_active

        product.save()

        status = True if product.is_active else False
        if status:
            messages.success(
                request, f"{product.name} is Listed Successfuly", extra_tags="admin"
            )
        else:
            messages.error(
                request, f"{product.name} is Unlisted Successfuly", extra_tags="admin"
            )
    else:
        messages.error(request, "Invalid request method.", extra_tags="admin")

    return redirect("admin_products")

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class AdminCategoryView(ListView):
    model = Category
    template_name = "categorys/category.html"
    context_object_name = "categorys"
    paginate_by = 9
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search", "")
        category_status = self.request.GET.get("category_status", "")
        if category_status == "active":
            queryset = queryset.filter(is_active=True)
        elif category_status == "blocked":
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.annotate(count=Count("products"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context["custom_page_range"] = paginator.get_elided_page_range(
                number=page_obj.number, on_each_side=5, on_ends=1
            )
        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]
        context["search"] = self.request.GET.get("search", "")
        context["status"] = self.request.GET.get("category_status", "")
        return context

@staff_member_required(login_url='admin_login')
@require_POST
@never_cache
@transaction.atomic
def toggle_category_block(request, id):
    """
    Toggle a Category's active status and apply the same to its related Products.
    """
    category = get_object_or_404(Category, id=id)

    # Toggle category active status
    category.is_active = not category.is_active
    category.save()

    # Apply same status to related products
    new_status = category.is_active
    products = category.products.all()
    count = products.count()
    products.update(is_active=new_status)

    if new_status:
        # Category has been unblocked
        messages.success(
            request,
            f"{category.name} & related <strong>{count}</strong> products were unblocked successfully.",
            extra_tags="admin",
        )
    else:
        # Category has been blocked
        messages.success(
            request,
            f"{category.name} & related <strong>{count}</strong> products were blocked successfully.",
            extra_tags="admin",
        )

    return redirect("admin_category")

@staff_member_required(login_url='admin_login')
@never_cache
@transaction.atomic
def admin_category_management(request, id=None):
    """
    This is used to add new Categorys
    """
    category = get_object_or_404(Category, id=id) if id else None
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            category = form.save()
            if id:
                messages.success(
                    request,
                    f"{category.name} Category Updated Successfuly",
                    extra_tags="admin",
                )
            else:
                messages.success(
                    request,
                    f"{category.name} Category Added Successfully",
                    extra_tags="admin",
                )
            return redirect("admin_category")

        messages.error(request, "Please Fix the Errors", extra_tags="admin")
        return render(request, "categorys/admin_category_form.html", {"form": form})
    else:
        form = CategoryForm(instance=category)

    context = {"form": form, "category": category}

    return render(request, "categorys/admin_category_form.html", context)

