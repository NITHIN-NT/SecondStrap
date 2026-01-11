import json
import logging
import os
logger = logging.getLogger(__name__)

from django.views.decorators.cache import never_cache
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db import transaction
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models.functions import TruncDay,TruncYear,TruncHour
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required

from ..decorators import  redirect_if_authenticated
from ..forms import (AdminLoginForm,AdminForgotPasswordEmailForm,AdminSetNewPassword,AdminVerifyOTPForm,)
from ..utils import send_html_mail
from accounts.models import CustomUser, EmailOTP
from userFolder.order.models import OrderMain,OrderItem
from userFolder.wallet.models import *
from products.contact_models import ContactModel,Thumbanails
from products.models import Product
from coupon.models import *


def custom_404_handler(request, exception):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_home')
    else:
        return redirect('admin_login')

# Create your views here.
@never_cache
@redirect_if_authenticated
def admin_login(request):
    form = AdminLoginForm(request.POST)
    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(username=email, password=password)
            if user is None:
                messages.error(request,"Invalid email or password.",extra_tags="admin")
                return redirect("admin_login")
            
            if not user.is_active:
                messages.error(request,"Your account is inactive. Contact support.",extra_tags="admin")
                return redirect("admin_login")
            if not user.is_superuser:
                messages.error(request,"You do not have admin access.",extra_tags="admin")
                return redirect("admin_login")
            
            login(request, user)
            messages.success(request, f"Welcome {user.first_name}")
            return redirect("admin_home")
    return render(request, "adminAuth/login.html", {"form": form})

@never_cache
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

@never_cache
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

@never_cache
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

@never_cache
@staff_member_required(login_url='admin_login')
def admin_logout(request):
    if not request.user.is_authenticated and not request.user.is_superuser:
        return redirect('admin_login')
 
    logout(request)
    return redirect("admin_login")

@never_cache
@login_required(login_url='admin_login')
@staff_member_required(login_url='admin_login')
def admin_home(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('filter'):
        filter_type = request.GET.get('filter', 'all')
        
        base_data = OrderMain.objects.filter(order_status='delivered')
        end_date = timezone.now()
        
        if filter_type == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            base_data = base_data.filter(created_at__gte=start_date, created_at__lte=end_date)
            trunc_function = TruncHour
            date_format = "%I:%M %p"
            
        elif filter_type == 'last7':
            start_date = end_date - timedelta(days=7)
            base_data = base_data.filter(created_at__gte=start_date, created_at__lte=end_date)
            trunc_function = TruncDay
            date_format = "%b %d"
            
        elif filter_type == 'last30':
            start_date = end_date - timedelta(days=30)
            base_data = base_data.filter(created_at__gte=start_date, created_at__lte=end_date)
            trunc_function = TruncDay
            date_format = "%b %d"
            
        else: 
            trunc_function = TruncYear
            date_format = "%Y"
        
        base_data = (
            base_data
            .annotate(day=trunc_function("created_at"))
            .values("day")
            .annotate(total=Sum("final_price"))
            .order_by("day")
        )
        
        labels = [row["day"].strftime(date_format) for row in base_data]
        data = [float(row["total"] or 0) for row in base_data]
        
        return JsonResponse({
            'labels': labels,
            'data': data
        })
    
    today_start = timezone.now().replace(hour=0, minute=0, second=0)
    today_end = timezone.now()
    
    base_data = (OrderMain.objects.filter(order_status='delivered',created_at__gte=today_start,created_at__lte=today_end)
        .annotate(day=TruncHour("created_at"))
        .values("day")
        .annotate(total=Sum("final_price"))
        .order_by("day")
    )
    
    labels = [row["day"].strftime("%I:%M %p") for row in base_data]
    data = [float(row["total"] or 0) for row in base_data]
    
    target_statuses = [
        'pending', 'confirmed', 'shipped', 
        'out_for_delivery', 'delivered', 
        'cancelled', 'returned'
    ]
    
    order = OrderMain.objects.filter(order_status__in=target_statuses).values('order_status').annotate(count=Count('order_status'))
    
    order_labels = [item['order_status'] for item in order]
    order_data = [item['count'] for item in order]
    top_products = (OrderItem.objects
                    .filter(order__order_status = 'delivered')
                    .values('variant__product__name','variant__product__category__name')
                    .annotate(total_sold=Sum('quantity')) 
                    .order_by('-total_sold')[:5])
    
    top_categories = (OrderItem.objects.filter(order__order_status='delivered') 
                    .values('variant__product__category__name') 
                    .annotate(total_revenue=Sum('price_at_purchase')) 
                    .order_by('-total_revenue')[:5])
    
    if top_categories:
        max_revenue = top_categories[0]['total_revenue']
        for cat in top_categories:
            cat['percentage'] = (cat['total_revenue'] / max_revenue * 100) if max_revenue > 0 else 0
    context = {
        "order_labels": json.dumps(order_labels),
        "order_data": json.dumps(order_data),
        "sales_labels": json.dumps(labels),
        "sales_data": json.dumps(data),
        "total_users": CustomUser.objects.count(),
        "total_products": Product.objects.count(),
        "total_orders": OrderMain.objects.count(),
        "total_revenue": OrderMain.objects.filter(order_status='delivered', payment_status='paid').aggregate(total_revenue=Sum("final_price")),
        "recent_orders": OrderMain.objects.all()[:2],
        "top_products" : top_products,
        "top_categories":top_categories,
    }
    
    return render(request, 'dashboard/dashboard.html', context)

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class CustomerMessageView(ListView):  # Fixed typo
    model = ContactModel
    template_name = 'contact/customer_messages.html'
    context_object_name = 'customer_messages'
    ordering = '-created_at'  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_count"] = ContactModel.objects.filter(is_read=False).count()
        return context

@staff_member_required(login_url='admin_login')
@require_POST
@never_cache
def mark_message_read(request):
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        print('message_id')
        
        if not message_id:
            return JsonResponse({"success": False, "error": "Message ID required"}, status=400)

        with transaction.atomic():
            # transation and select for updated is used to avoid the race condition.
            message = ContactModel.objects.select_for_update().get(id=message_id)

            if not message.is_read:
                message.is_read = True
                message.save(update_fields=["is_read"])

            unread_count = ContactModel.objects.filter(is_read=False).count()

        return JsonResponse({
            "success": True,
            "unread_count": unread_count
        })

    except ContactModel.DoesNotExist:
        return JsonResponse({"success": False, "error": "Message not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": "Server error"}, status=500)
    
@staff_member_required(login_url='admin_login')
@never_cache
def thumbanail_view(request):
    thumbnails = Thumbanails.objects.all().order_by('-created_at')
    context = {
        'thumbnails' : thumbnails
    }
    return render(request,'thumbnails/thumbanail.html',context)

@staff_member_required(login_url='admin_login')
@never_cache
@require_POST
def upload_thumbnail(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        image_name = request.POST.get('name', 'Untitled')
        
        if not image_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)
        
        extension = os.path.splitext(image_file.name)[1].lower()
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.webp']
    
        if extension not in allowed_extensions:
            return JsonResponse({'success': False, 
                'error': f'Unsupported file format. Allowed: {", ".join(allowed_extensions)}'
            }, status=400)
        
        try:
            thumbnail = Thumbanails.objects.create(
                name=image_name,
                image=image_file
            )

            return JsonResponse({'success': True,'image_id': thumbnail.id,
                'image_url': thumbnail.image.url,
                'name': thumbnail.name
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
@staff_member_required(login_url='admin_login')
@never_cache
@require_POST
def delete_thumbnail(request,image_id):
    thumbanail = get_object_or_404(Thumbanails,id=image_id)
    thumbanail.delete()
    return JsonResponse({'success':True})

@staff_member_required(login_url='admin_login')
@never_cache
@require_POST
def toggle_visibility_view(request,image_id):
    thumbanail = get_object_or_404(Thumbanails,id=image_id)
    thumbanail.is_visible = not thumbanail.is_visible
    thumbanail.save()
    
    return JsonResponse({'success':True})