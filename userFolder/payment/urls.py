from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.create_razorpay_order, name='create_razorpay_order'),
    path('success/', views.razorpay_callback, name='razorpay_callback'),
]
