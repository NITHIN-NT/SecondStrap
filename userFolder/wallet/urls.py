from django.urls import path
from django.views.generic import TemplateView
from .views import *
from .views import wallet_top_up_success_view

urlpatterns = [
    path('add/',create_wallet_razorpay_order,name='create_wallet_razorpay_order'),
    path('success/',wallet_razorpay_callback,name='wallet_razorpay_callback'),
    path('failure/', TemplateView.as_view(template_name='wallet/wallet_failure.html'), name='wallet_top_up_failure'),
    path('topup-success/', wallet_top_up_success_view, name='wallet_top_up_success'),
    path('payment/',pay_using_wallet,name='pay_using_wallet'),
]