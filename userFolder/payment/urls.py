from django.urls import path
from . import views

urlpatterns = [
    path('deduct-wallet/', views.deduct_amount_from_wallet, name='deduct_amount_from_wallet'),
    path('start/', views.create_razorpay_order, name='create_razorpay_order'),
    path('success/', views.razorpay_callback, name='razorpay_callback'),
]
