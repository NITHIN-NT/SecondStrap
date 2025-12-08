import json
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, ListView, DetailView

from django.template.loader import render_to_string

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test

from django.db.models import Count, Sum
from django.db import transaction
from django.db.models import Q , F

from django.forms import inlineformset_factory
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404

from .decorators import superuser_required, redirect_if_authenticated
from .forms import (
    AdminLoginForm,
    AdminForgotPasswordEmailForm,
    AdminSetNewPassword,
    AdminVerifyOTPForm,
    VariantForm,
    ImageForm,
    AdminProductAddForm,
    VariantFormSet,
    ImageFormSet,
    CategoryForm,
)
from .utils import send_html_mail

from accounts.models import CustomUser, EmailOTP
from products.models import Product, Category, ProductVariant, ProductImage
from userFolder.order.models import OrderMain,OrderItem,ReturnOrder,ORDER_STATUS_CHOICES,PAYMENT_STATUS_CHOICES,ADMIN_ORDER_STATUS_CHOICES
from userFolder.wallet.models import *
from django.views.decorators.http import require_POST
from django.http import JsonResponse

import logging
logger = logging.getLogger(__name__)

# Create your views here.
@never_cache
@redirect_if_authenticated
def admin_login(request):
    if request.method == "POST":
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(username=email, password=password)
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect("admin_home")
            else:
                messages.error(
                    request,
                    "Invalid email or password, or you don't have admin access.",
                    extra_tags="admin",
                )
                return redirect("admin_login")
    else:
        form = AdminLoginForm()
    return render(request, "adminAuth/login.html", {"form": form})


@redirect_if_authenticated
def admin_forgot(request):
    form = AdminForgotPasswordEmailForm()
    if request.method == "POST":
        form = AdminForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                messages.error(
                    request, "No User Found With this email", extra_tags="admin"
                )
                return redirect("admin_login")

            if not user.is_superuser:
                messages.error(
                    request,
                    "Access denied. Only admins can reset password here.",
                    extra_tags="admin",
                )
                return redirect("admin_login")

            if "admin_reset_password_allowed" in request.session:
                del request.session["admin_reset_password_allowed"]

            otp_code = EmailOTP.generate_otp()
            EmailOTP.objects.create(user=user, otp=otp_code)

            subject = "Admin Reset Password One-Time-Password "

            try:
                send_html_mail(
                    subject=subject,
                    template_name="email/admin_otp_email.html",
                    context={"otp_code": otp_code},
                    to_email=email,
                    plain_text=f"Your OTP code for password Rest is :{otp_code}",
                )
                request.session["reset_admin_email"] = user.email
                messages.success(
                    request, f"An OTP has been Sent to {email}", extra_tags="admin"
                )
                return redirect("admin_otp_verification")

            except Exception as e:
                print("Email sending failed:", e)
                messages.error(
                    request,
                    "There was an error sending the email. Please try again later.",
                    extra_tags="admin",
                )
                return redirect("admin_forgot_password")
    return render(request, "adminAuth/forgot-password.html", {"form": form})


@redirect_if_authenticated
def admin_otp_verification(request):

    if not request.session.get("reset_admin_email"):
        messages.error(
            request, "You are Not autherized to access this page.", extra_tags="admin"
        )
        return redirect("admin_login")
    email = request.session.get("reset_admin_email")
    if not email:
        messages.error(
            request, "Your Session has expired. Please Start Over", extra_tags="admin"
        )
        return redirect("admin_forgot_password")
    if request.method == "POST":
        form = AdminVerifyOTPForm(request.POST)
        if form.is_valid():
            otp_from_form = form.cleaned_data["otp"]
            user = get_object_or_404(CustomUser, email=email)

            try:
                email_otp = EmailOTP.objects.filter(user=user).latest("created_at")
            except EmailOTP.DoesNotExist:
                messages.error(
                    request, "No OTP found,Please request New One", extra_tags="admin"
                )
                return redirect("admin_forgot_password")

            if email_otp.otp == otp_from_form and email_otp.is_valid():
                email_otp.delete()

                request.session["admin_reset_password_allowed"] = True

                messages.success(
                    request,
                    "OTP verified successfully. Please set your new password",
                    extra_tags="admin",
                )
                return redirect("admin_reset")
            elif not email_otp.is_valid():
                messages.error(
                    request,
                    "Your OTP has expired. Please request a new one.",
                    extra_tags="admin",
                )
            else:
                messages.error(
                    request,
                    "Invalid or expired OTP. Please try again.",
                    extra_tags="admin",
                )
    else:
        form = AdminVerifyOTPForm()
    return render(request, "adminAuth/otp-verification.html", {"form": form})


@redirect_if_authenticated
def admin_reset(request):
    if not request.session.get(
        "admin_reset_password_allowed"
    ) or not request.session.get("reset_admin_email"):
        messages.error(
            request,
            "You are not authorized to access this page. Please verify your OTP first.",
            extra_tags="admin",
        )
        return redirect("admin_forgot_password")

    email = request.session.get("reset_admin_email")

    if not email or not request.session.get("admin_reset_password_allowed"):
        messages.error(
            request, "Your session has expired. Please start over.", extra_tags="admin"
        )
        return redirect("admin_forgot_password")

    if request.method == "POST":
        form = AdminSetNewPassword(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]
            user = get_object_or_404(CustomUser, email=email)

            user.set_password(new_password)
            user.save()
            messages.success(
                request,
                "Your password has been reset successfully. Please log in.",
                extra_tags="admin",
            )
            try:
                del request.session["reset_admin_email"]
                del request.session["admin_reset_password_allowed"]
            except KeyError:
                pass
            return redirect("admin_login")
    else:
        form = AdminSetNewPassword()
    return render(request, "adminAuth/reset-password.html", {"form": form})


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


@method_decorator([never_cache, superuser_required], name="dispatch")
class AdminHome(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_users"] = CustomUser.objects.all().count()
        context["total_products"] = Product.objects.all().count()
        """
            Total orders is fake you need to add when you create the orders
        """
        context["total_orders"] = "02"
        context["total_revenue"] = "02"
        return context


@method_decorator([never_cache, superuser_required], name="dispatch")
class AdminUserView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = "users/home_user.html"
    context_object_name = "Users"
    ordering = ["-date_joined"]
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("search_input", "")
        user_status = self.request.GET.get("userStatus", "")
        if user_status == "active":
            queryset = queryset.filter(is_active=True)
        elif user_status == "blocked":
            queryset = queryset.filter(is_active=False)

        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
            )

        return queryset

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

        context["search_input"] = self.request.GET.get("search_input", "")
        context["user_status"] = self.request.GET.get("userStatus", "")
        return context


@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
@transaction.atomic
def toggle_user_block(request, id):
    if request.method == "POST":
        user = get_object_or_404(CustomUser, id=id)
        user.is_active = not user.is_active

        user.save()

        status = True if user.is_active else False
        if status:
            messages.success(
                request, f"{user.email} is Unblockd Successfuly", extra_tags="admin"
            )
        else:
            messages.error(
                request, f"{user.email} is Blocked Successfuly", extra_tags="admin"
            )
            return redirect("admin_user")
    else:
        messages.warning(request, "Invalid request method.", extra_tags="admin")
    return redirect("admin_user")


@method_decorator([never_cache, superuser_required], name="dispatch")
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


@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
@transaction.atomic
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


@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
@transaction.atomic
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


@method_decorator([never_cache, superuser_required], name="dispatch")
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


@require_POST
@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
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


@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
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


@method_decorator([never_cache, superuser_required], name="dispatch")
class StockManagementView(ListView):
    model = Product
    context_object_name = "products"
    template_name = "stock/stock_management.html"
    paginate_by = 9

    def get_queryset(self, **kwargs):
        return Product.objects.annotate(
            total_stock=Sum("variants__stock"), variant_count=Count("variants")
        ).prefetch_related("variants", "variants__size")
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context['custom_page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=2,
                on_ends=1
            )

        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        encoded = query_params.urlencode()
        context['query_params'] = encoded  
        return context

@method_decorator([never_cache, superuser_required], name="dispatch")
class AdminOrderView(ListView):
    model = OrderMain
    context_object_name = 'orders'
    template_name ='order/order.html'
    ordering = ['-created_at']
    paginate_by = 9
    
    def get_queryset(self):
        queryset =  super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        payment = self.request.GET.get('payment')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if search:
            queryset = queryset.filter(order_id__icontains = search.strip())
            
        if status:
            queryset = queryset.filter(order_status__icontains = status)
        
        if payment:
            queryset = queryset.filter(payment_status__icontains = payment)
            
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__range =[start_date,end_date])
        elif start_date :
            queryset = queryset.filter(created_at__date__gte=start_date)
        elif end_date :
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        return queryset
        
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context['custom_page_range'] = paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=5,
                on_ends=1
            )

        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        encoded = query_params.urlencode()
        context['query_params'] = encoded  

        context['order_status_choices'] = ORDER_STATUS_CHOICES
        context['payment_status_choices'] = PAYMENT_STATUS_CHOICES
        return context

    
@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")   
def admin_order_detailed_view(request,order_id):
    order = get_object_or_404(OrderMain, order_id=order_id)
    context = {
        'order' : order,
        'order_status_choices': ADMIN_ORDER_STATUS_CHOICES, 
        'payment_status_choices': PAYMENT_STATUS_CHOICES,
    }
    return render(request,'order/order_detailed.html',context)
  
@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
@transaction.atomic
def admin_order_status_update(request,order_id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)
    
    try :
        order_status = request.POST.get('order_status')
        payment_status = request.POST.get('payment_status')
        
        if not order_status or not payment_status:
            return JsonResponse(
                {"status": "error", "message": "Missing status values"},
                status=400
            )
        
        order = get_object_or_404(OrderMain,order_id=order_id)
        
        if order.order_status != 'cancelled' and order_status == 'cancelled':
            for item in order.items.all():
                if item.variant:
                    item.variant.stock = F('stock') + item.quantity
                    item.variant.save()
        
        order.order_status = order_status
        order.payment_status = payment_status
        order.save()
        
        ignored_statuses = [
            'cancelled', 
            'returned', 
            'return_requested', 
            'return_approved', 
            'return_rejected', 
            'return_canceled'
        ]
        order.items.exclude(status__in = ignored_statuses).update(status=order_status)
            
        return JsonResponse({"status" : 'success' , "message":"Order Status updated !"})
    except Exception as e :
        print(f"Error updating order {order_id}: {str(e)}")
        logger.exception("Failed to update order status for order %s", order_id)
        return JsonResponse({'status': 'error', 'message': 'Update failed'})
    
@login_required
@user_passes_test(lambda user: user.is_superuser, login_url="admin_login")
@transaction.atomic
def manage_return_request(request,item_id,order_id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid Request"}, status=405)

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        action = data.get('action')
        
        if action not in {'approve', 'reject', 'returned'}:
            return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)
                
    
        order = get_object_or_404(OrderMain,order_id=order_id)
        order_item = get_object_or_404(OrderItem,id=item_id,order__order_id=order_id)
        product_variant = order_item.variant
        
        return_item = ReturnOrder.objects.filter(order=order,item=order_item).first()
        
        if not return_item:
            return JsonResponse({"status": "error", "message": "No return request found"}, status=400)
    
        # Approve
        if action == 'approve':
            
            if order_item.status != 'return_requested':
                return JsonResponse({"status": "error", "message": "Item is not in requested state"}, status=400)
            
            order_item.status = 'return_approved'
            order_item.save()
            
            return_item.return_status = 'return_approved'
            return_item.save()
            
            if order_item.status != 'returned':
                order.order_status = 'return_approved'
                order.save()
                
            return JsonResponse({"status": "success", "message": "Return approved"})

        # Reject
        elif action == 'reject':
            
            if order_item.status != 'return_requested':
                return JsonResponse({"status": "error", "message": "Item is not in requested state"}, status=400)
           
            order_item.status = 'delivered'
            order_item.is_returned = False
            order_item.save()
            
            return_item.return_status = 'return_rejected'    
            return_item.save()
            
            return JsonResponse({"status": "success", "message": "Return rejected"})
        
        elif action == 'returned':
            
            if order_item.status != 'return_approved':
                return JsonResponse({"status": "error", "message": "Item must be approved before receiving"}, status=400)
            
            order_item.status = 'returned'
            order_item.is_returned = True
            
            return_item.return_status = 'returned'
            refund_amount = order_item.price_at_purchase * order_item.quantity
            return_item.refund_amount = refund_amount
            
            if product_variant :
                product_variant.stock = F('stock') + order_item.quantity
                product_variant.save()
                product_variant.refresh_from_db() # This line is used to refresh the DB and collect the latest value
                
            active_items_exist = order.items.filter(is_returned=False).exists()
            
            if not active_items_exist:
                order.order_status = 'partially_returned'
            else:
                order.order_status = 'returned'
                
            
            
            try:
                # Refunding the amount to the Wallet
                wallet_user = order.user
                wallet,created = Wallet.objects.get_or_create(
                    user=wallet_user
                )
                
                Wallet.objects.filter(pk=wallet.pk).update(
                    balance = F('balance') + refund_amount
                )
                
                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type=TransactionType.CREDIT,
                    amount=return_item.refund_amount,
                    description=f"Refund for Item: {order_item.variant.product.name if order_item.variant else order_item.product.name}",
                    status=TransactionStatus.COMPLETED,
                    related_order = order
                )
            except Exception as E:
                print(f"Error processing refund: {E}")
                
            order_item.save()
            return_item.save()
            order.save()
            return JsonResponse({'status': 'success', 'message': 'Item marked as Received'})
            
        else:
            return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)

    except Exception as e:
        print('return execption : ',str(e))  
        return JsonResponse({"status": "error", "message": "Internal Server Error"}, status=500)
        