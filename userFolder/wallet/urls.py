from django.urls import path
from .views import *
urlpatterns = [
    path('add/',create_wallet_razorpay_order,name='create_wallet_razorpay_order'),
    path('success/',wallet_razorpay_callback,name='wallet_razorpay_callback'),
    path('payment/',pay_using_wallet,name='pay_using_wallet')
]