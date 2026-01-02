from django.urls import path
from . import views

urlpatterns = [
    path('coupon-apply/', views.apply_coupon, name='coupon_discount'),
    path('coupon-remove/', views.remove_coupon, name='remove_coupon'),
    path('deduct-wallet/', views.deduct_amount_from_wallet, name='deduct_amount_from_wallet'),
    path('start/', views.create_razorpay_order, name='create_razorpay_order'),
    path('success/', views.razorpay_callback, name='razorpay_callback'),
    
    path('failed/log/', views.payment_failed_log, name='payment_failed_logging'),
    path('failed/', views.payment_failed_page, name='payment_failed_page'),
]
