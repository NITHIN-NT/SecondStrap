from django.urls import path
from .views import *
urlpatterns = [
    path('add/',create_wallet_razorpay_order,name='create_wallet_razorpay_order'),
    path('success/',wallet_razorpay_callback,name='wallet_razorpay_callback'),
    path('failure/', lambda r: render(r, 'orders/order_error.html'), name='wallet_top_up_failure'),
    path('payment/',pay_using_wallet,name='pay_using_wallet'),
]